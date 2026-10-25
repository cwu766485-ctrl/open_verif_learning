"""Single owner for both packed CPU lanes in Python subsystem tests."""

from dataclasses import dataclass

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
        self.cycle = 0
        self.latencies = {0: [], 1: []}
        self.request_stall_cycles = {0: 0, 1: 0}
        self.response_stall_cycles = {0: 0, 1: 0}

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
                          response_stall_cycles: int = 0):
        if response_stall_cycles < 0:
            raise ValueError("response_stall_cycles must be non-negative")
        reqs = (core0, core1)
        desired, write, mask, addr, data = self._pack(reqs)
        if not desired:
            raise ValueError("access_pair requires at least one request")
        d = self.dut
        d.cpu_resp_ready.value = 0
        d.cpu_req_addr.value = addr
        d.cpu_req_write.value = write
        d.cpu_req_wmask.value = mask
        d.cpu_req_wdata.value = data
        d.cpu_req_valid.value = desired
        accepted = 0
        accepted_at = {}

        for _ in range(max_cycles):
            await ClockCycles(d, 1)
            self.cycle += 1
            ready = int(d.cpu_req_ready.value)
            for core in range(2):
                bit = 1 << core
                if (desired & bit) and not (accepted & bit) and not (ready & bit):
                    self.request_stall_cycles[core] += 1
            newly = desired & ~accepted & ready
            for core in range(2):
                if newly & (1 << core):
                    accepted_at[core] = self.cycle
            accepted |= newly
            d.cpu_req_valid.value = desired & ~accepted
            if accepted == desired:
                break
        else:
            d.cpu_req_valid.value = 0
            raise TimeoutError(
                f"CPU requests not accepted: wanted={desired:02b} accepted={accepted:02b} "
                f"ready={int(d.cpu_req_ready.value):02b}"
            )
        d.cpu_req_valid.value = 0

        results = [None, None]
        latched = 0
        held_payload = {}
        stall_remaining = {}
        for _ in range(max_cycles):
            await ClockCycles(d, 1)
            self.cycle += 1
            valid = int(d.cpu_resp_valid.value) & desired
            ready_mask = 0
            packed_data = int(d.cpu_resp_rdata.value)
            packed_addr = int(d.cpu_resp_addr.value)
            packed_write = int(d.cpu_resp_write.value)
            for core in held_payload:
                if not (valid & (1 << core)):
                    raise AssertionError(
                        f"core{core} response valid dropped while ready was low"
                    )
            for core, req in enumerate(reqs):
                bit = 1 << core
                if not req or not (valid & bit) or (latched & bit):
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
                self.latencies[core].append(self.cycle - accepted_at[core])
                ready_mask |= bit
            latched |= ready_mask
            d.cpu_resp_ready.value = ready_mask
            if latched == desired:
                await ClockCycles(d, 1)
                self.cycle += 1
                d.cpu_resp_ready.value = 0
                return tuple(results)
        d.cpu_resp_ready.value = 0
        raise TimeoutError(
            f"CPU response timeout for mask={desired:02b}; valid="
            f"{int(d.cpu_resp_valid.value):02b} protocol_error={int(d.protocol_error.value)}"
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
