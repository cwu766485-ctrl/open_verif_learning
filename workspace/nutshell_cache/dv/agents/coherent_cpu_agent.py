"""Single owner for both packed CPU lanes in Python subsystem tests."""

from dataclasses import dataclass
from typing import Callable

from toffee import ClockCycles


@dataclass(frozen=True)
class CpuRequest:
    addr: int
    write: bool = False
    data: int = 0
    mask: int = 0xFF


class DualCoreCpuDriver:
    """Drive both cores without competing assignments to packed DUT pins.

    ``access_pair`` accepts zero, one, or two requests in the same cycle and
    independently retires their responses. The convenience ``access`` API is
    intentionally implemented by this same packed-port owner.
    """

    def __init__(self, dut):
        self.dut = dut
        # Optional callback for sampled CPU handshakes.  The graybox monitor
        # also observes the pins, but Toffee scheduling can make it miss an
        # edge when this driver resumes in another scheduler group.
        self.observation_callback = None
        self.cycle = 0
        self.latencies = {0: [], 1: []}
        self.request_stall_cycles = {0: 0, 1: 0}
        self.response_stall_cycles = {0: 0, 1: 0}
        self.last_pair_accepted_at = {}
        self.last_pair_completed_at = {}
        self.transactions = []
        self.request_group = 0

    @staticmethod
    def _pack(reqs):
        valid = write = mask = addr = data = 0
        for core, req in enumerate(reqs):
            if req is None:
                continue
            valid |= 1 << core
            if req.write:
                write |= 1 << core
                mask |= (req.mask & 0xFF) << (8 * core)
            addr |= (req.addr & 0xFFFFFFFF) << (32 * core)
            data |= (req.data & ((1 << 64) - 1)) << (64 * core)
        return valid, write, mask, addr, data

    async def access_pair(self, core0: CpuRequest | None,
                          core1: CpuRequest | None,
                          *, max_cycles: int = 1000,
                          response_stall_cycles: int = 0,
                          request_delay_cycles: dict[int, int] | None = None,
                          request_release_predicates:
                          dict[int, Callable[[], bool]] | None = None):
        if response_stall_cycles < 0:
            raise ValueError("response_stall_cycles must be non-negative")
        reqs = (core0, core1)
        request_group = self.request_group
        self.request_group += 1
        desired, write, mask, addr, data = self._pack(reqs)
        if not desired:
            raise ValueError("access_pair requires at least one request")
        delays = request_delay_cycles or {}
        if any(core not in (0, 1) or reqs[core] is None or delay < 0
               for core, delay in delays.items()):
            raise ValueError("request delays must name present cores and be non-negative")
        delays = {core: delays.get(core, 0) for core in range(2)}
        release_predicates = request_release_predicates or {}
        if any(core not in (0, 1) or reqs[core] is None or
               not callable(predicate)
               for core, predicate in release_predicates.items()):
            raise ValueError(
                "request release predicates must name present cores and be callable"
            )

        def release_ready(core, cycle):
            predicate = release_predicates.get(core)
            return (delays[core] <= cycle and
                    (predicate is None or bool(predicate())))

        d = self.dut
        d.cpu_resp_ready.value = 0
        d.cpu_req_addr.value = addr
        d.cpu_req_write.value = write
        d.cpu_req_wmask.value = mask
        d.cpu_req_wdata.value = data
        offered = sum(1 << core for core, req in enumerate(reqs)
                      if req is not None and release_ready(core, 0))
        d.cpu_req_valid.value = offered
        accepted = 0
        accepted_at = {}
        results = [None, None]
        completed_at = {}
        completed = 0
        held_payload = {}
        stall_remaining = {}
        response_trace = []
        pending_resp_ready = 0
        pending_response_info = {}
        seen_valid = 0
        for _ in range(max_cycles):
            await ClockCycles(d, 1)
            self.cycle += 1

            # The response handshake driven in the previous iteration has
            # now retired. Keep request acceptance and response retirement in
            # one loop: a serialized target (for example, MMIO) may not accept
            # lane 1 until lane 0's response is consumed.
            for core in range(2):
                bit = 1 << core
                if pending_resp_ready & bit:
                    completed |= bit
                    completed_at[core] = self.cycle
                    if self.observation_callback is not None:
                        self.observation_callback(
                            "response_complete", pending_response_info[core]
                        )
            pending_resp_ready = 0

            req_ready = int(d.cpu_req_ready.value)
            newly = offered & ~accepted & req_ready
            for core in range(2):
                bit = 1 << core
                if newly & bit:
                    accepted_at[core] = self.cycle
                    if self.observation_callback is not None:
                        self.observation_callback("request_accept", {
                            "core": core,
                            "address": reqs[core].addr & 0xFFFF_FFFF,
                            "write": int(reqs[core].write),
                        })
                elif ((desired & bit) and not (accepted & bit) and
                      (offered & bit)):
                    self.request_stall_cycles[core] += 1
            accepted |= newly

            valid = int(d.cpu_resp_valid.value) & desired
            seen_valid |= valid
            response_trace.append((self.cycle, valid,
                                   int(d.cpu_resp_ready.value),
                                   int(d.cpu_resp_addr.value),
                                   int(d.cpu_resp_write.value)))
            if len(response_trace) > 16:
                response_trace.pop(0)
            ready_mask = 0
            packed_data = int(d.cpu_resp_rdata.value)
            packed_addr = int(d.cpu_resp_addr.value)
            packed_write = int(d.cpu_resp_write.value)
            packed_txn_id = int(d.cpu_resp_txn_id.value)
            for core in held_payload:
                if not (valid & (1 << core)):
                    raise AssertionError(
                        f"core{core} response valid dropped while ready was low"
                    )
            for core, req in enumerate(reqs):
                bit = 1 << core
                if (not req or not (accepted & bit) or not (valid & bit) or
                        (completed & bit) or (pending_resp_ready & bit)):
                    continue
                got_addr = (packed_addr >> (32 * core)) & 0xFFFFFFFF
                got_write = (packed_write >> core) & 1
                got_data = (packed_data >> (64 * core)) & ((1 << 64) - 1)
                if got_addr != (req.addr & 0xFFFFFFFF) or got_write != int(req.write):
                    raise AssertionError(
                        f"core{core} response mismatch: {got_addr:#x}/{got_write}, "
                        f"expected {req.addr:#x}/{int(req.write)}"
                    )
                payload = (got_addr, got_write, got_data)
                if core in held_payload and held_payload[core] != payload:
                    raise AssertionError(
                        f"core{core} response changed under backpressure: "
                        f"{held_payload[core]} -> {payload}"
                    )
                if core not in held_payload and response_stall_cycles:
                    held_payload[core] = payload
                    stall_remaining[core] = response_stall_cycles
                if core in stall_remaining and stall_remaining[core] > 0:
                    stall_remaining[core] -= 1
                    self.response_stall_cycles[core] += 1
                    if stall_remaining[core] > 0:
                        continue
                results[core] = got_data
                ready_mask |= bit
                pending_response_info[core] = {
                    "core": core,
                    "address": got_addr,
                    "write": got_write,
                    "data": got_data,
                    "txn_id": (packed_txn_id >> (3 * core)) & 0x7,
                }
                held_payload.pop(core, None)
                stall_remaining.pop(core, None)
            pending_resp_ready = ready_mask

            next_cycle = _ + 1
            offered = sum(1 << core for core, req in enumerate(reqs)
                          if req is not None and not (accepted & (1 << core))
                          and release_ready(core, next_cycle))
            self.last_pair_accepted_at = dict(accepted_at)
            d.cpu_req_valid.value = offered
            d.cpu_resp_ready.value = ready_mask
            if accepted == desired and completed == desired:
                d.cpu_req_valid.value = 0
                d.cpu_resp_ready.value = 0
                self.last_pair_accepted_at = dict(accepted_at)
                self.last_pair_completed_at = dict(completed_at)
                for core, req in enumerate(reqs):
                    if req is None:
                        continue
                    latency = completed_at[core] - accepted_at[core]
                    self.latencies[core].append(latency)
                    self.transactions.append({
                        "accepted_cycle": accepted_at[core],
                        "response_cycle": completed_at[core],
                        "latency_cycles": latency,
                        "core": core,
                        "request_group": request_group,
                        "addr": req.addr & 0xFFFFFFFF,
                        "write": int(req.write),
                        "write_data": req.data & ((1 << 64) - 1),
                        "mask": req.mask & 0xFF,
                        "response_data": results[core],
                        "response_stall_cycles": response_stall_cycles,
                        "request_delay_cycles": delays[core],
                    })
                return tuple(results)
        d.cpu_resp_ready.value = 0
        d.cpu_req_valid.value = 0
        raise TimeoutError(
            f"CPU response timeout for mask={desired:02b}; valid="
            f"{int(d.cpu_resp_valid.value):02b} accepted={accepted:02b} "
            f"completed={completed:02b} seen={seen_valid:02b} "
            f"protocol_error={int(d.protocol_error.value)} "
            f"trace={response_trace}"
        )

    async def access(self, core: int, addr: int, *, write: bool = False,
                     data: int = 0, mask: int = 0xFF,
                     response_stall_cycles: int = 0,
                     max_cycles: int = 1000) -> int:
        if core not in (0, 1):
            raise ValueError("core must be 0 or 1")
        req = CpuRequest(addr, write, data, mask)
        result = await self.access_pair(req if core == 0 else None,
                                        req if core == 1 else None,
                                        max_cycles=max_cycles,
                                        response_stall_cycles=response_stall_cycles)
        return result[core]


class CoherentCpuAgent:
    """Compatibility facade; new tests should share one DualCoreCpuDriver."""

    def __init__(self, dut, core: int):
        if core not in (0, 1):
            raise ValueError("core must be 0 or 1")
        self.core = core
        self.driver = DualCoreCpuDriver(dut)

    async def access(self, addr: int, *, write: bool = False, data: int = 0,
                     max_cycles: int = 1000) -> int:
        return await self.driver.access(self.core, addr, write=write, data=data,
                                        max_cycles=max_cycles)
