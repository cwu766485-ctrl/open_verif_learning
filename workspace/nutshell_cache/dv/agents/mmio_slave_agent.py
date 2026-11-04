"""Handshake-accurate MMIO slave role for the integrated cache top."""

from collections import Counter, deque

from toffee import ClockCycles


class MmioSlaveAgent:
    """Single-outstanding MMIO slave with a byte-masked backing model.

    The cache's MMIO router issues one request at a time and has no external
    response ID. This agent deliberately models that contract instead of
    inventing an ID or allowing multiple responses to be outstanding.
    """

    def __init__(self, dut, *, request_stall_period=5, response_delay=2,
                 response_stall_period=7):
        if request_stall_period < 2 or response_stall_period < 2:
            raise ValueError("MMIO stall periods must be at least two")
        if response_delay < 0:
            raise ValueError("response_delay must be non-negative")
        self.dut = dut
        self.request_stall_period = request_stall_period
        self.response_stall_period = response_stall_period
        self.response_delay = response_delay
        self.cycle = 0
        self.words = {}
        self.requests = []
        self.completions = []
        self.stalls = Counter()
        self.reset_cancelled = 0
        self._held_request = None
        self._forced_request_stall = 0
        self.observation_callback = None

    def force_request_stall(self, cycles):
        """Hold request READY low for a deterministic number of active cycles.

        This controls the testbench slave only; it does not alter the DUT or
        bypass the normal request VALID/READY protocol checker.
        """
        if cycles < 1:
            raise ValueError("forced MMIO request stall must be at least one cycle")
        if self._forced_request_stall:
            raise RuntimeError("an MMIO request stall is already armed")
        self._forced_request_stall = cycles

    @staticmethod
    def _merge(old, data, mask):
        value = old
        for lane in range(8):
            if (mask >> lane) & 1:
                byte_mask = 0xFF << (8 * lane)
                value = (value & ~byte_mask) | (data & byte_mask)
        return value & ((1 << 64) - 1)

    async def run(self):
        d = self.dut
        d.mmio_req_ready.value = 0
        d.mmio_resp_valid.value = 0
        d.mmio_resp_rdata.value = 0
        pending = None
        response = None
        while True:
            self.cycle += 1
            if int(d.reset.value):
                self.reset_cancelled += int(pending is not None) + int(response is not None)
                pending = None
                response = None
                self._held_request = None
                d.mmio_req_ready.value = 0
                d.mmio_resp_valid.value = 0
                await ClockCycles(d, 1)
                continue

            if self._forced_request_stall:
                ready = 0
                self._forced_request_stall -= 1
            else:
                ready = int(self.cycle % self.request_stall_period != 0)
            d.mmio_req_ready.value = ready
            if response is None and pending is not None and pending["due"] <= self.cycle:
                response = pending
                pending = None
            resp_valid = response is not None
            d.mmio_resp_valid.value = int(resp_valid)
            if resp_valid:
                d.mmio_resp_rdata.value = response["data"]

            await ClockCycles(d, 1)
            # Reset can assert while this agent is suspended at the clock
            # edge. The synchronous reset cancels the held request, so skip
            # normal VALID/READY stability checks for that sampled edge.
            if int(d.reset.value):
                continue
            req = (
                int(d.mmio_req_addr.value), int(d.mmio_req_size.value),
                int(d.mmio_req_write.value), int(d.mmio_req_wmask.value),
                int(d.mmio_req_wdata.value),
            )
            req_valid = int(d.mmio_req_valid.value)
            req_fire = bool(req_valid and ready)
            resp_ready = int(d.mmio_resp_ready.value)
            resp_fire = bool(resp_valid and resp_ready)

            if self._held_request is not None and (not req_valid or req != self._held_request):
                raise AssertionError(
                    f"MMIO request changed while stalled: {self._held_request} -> {req}"
                )
            if req_valid and not ready:
                self._held_request = req
                self.stalls["request"] += 1
            else:
                self._held_request = None
            if resp_valid and not resp_ready:
                self.stalls["response"] += 1

            if req_fire:
                if pending is not None or response is not None:
                    raise AssertionError("MMIO source issued while prior response is active")
                addr, size, write, mask, data = req
                if size != 3:
                    raise AssertionError(f"MMIO request size is {size}, expected 64-bit size 3")
                aligned = addr & ~0x7
                old = self.words.get(aligned, 0)
                if write:
                    self.words[aligned] = self._merge(old, data, mask)
                    result = 0
                else:
                    result = old
                record = {"cycle": self.cycle, "addr": addr, "size": size,
                          "write": write, "mask": mask, "wdata": data,
                          "rdata": result}
                self.requests.append(record)
                if self.observation_callback is not None:
                    self.observation_callback("request_accept", record)
                pending = {"due": self.cycle + self.response_delay,
                           "data": result, "request": record}

            if resp_fire:
                completion = {"cycle": self.cycle,
                              "request": response["request"],
                              "data": response["data"]}
                self.completions.append(completion)
                if self.observation_callback is not None:
                    self.observation_callback("response_complete", completion)
                response = None
