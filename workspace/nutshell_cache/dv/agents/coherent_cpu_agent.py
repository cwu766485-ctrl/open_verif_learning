"""Python request/response driver for the packed dual-core cache wrapper."""

from toffee import ClockCycles


class CoherentCpuAgent:
    def __init__(self, dut, core: int):
        if core not in (0, 1):
            raise ValueError("core must be 0 or 1")
        self.dut = dut
        self.core = core
        self.mask = 1 << core

    async def access(self, addr: int, *, write: bool = False, data: int = 0,
                     max_cycles: int = 100) -> int:
        """Issue one CPU request and return its 64-bit response data."""
        d, c = self.dut, self.core
        d.cpu_resp_ready.value = 0
        d.cpu_req_addr.value = addr << (32 * c)
        d.cpu_req_write.value = self.mask if write else 0
        d.cpu_req_wmask.value = (0xFF << (8 * c)) if write else 0
        d.cpu_req_wdata.value = (data & ((1 << 64) - 1)) << (64 * c)
        d.cpu_req_valid.value = self.mask

        for _ in range(max_cycles):
            await ClockCycles(d, 1)
            if int(d.cpu_req_ready.value) & self.mask:
                break
        else:
            d.cpu_req_valid.value = 0
            raise TimeoutError(
                f"core{c} request was not accepted at {addr:#x}; "
                f"ready={int(d.cpu_req_ready.value):b}, reset={int(d.reset.value)}"
            )
        d.cpu_req_valid.value = 0

        for _ in range(max_cycles):
            await ClockCycles(d, 1)
            if int(d.cpu_resp_valid.value) & self.mask:
                packed = int(d.cpu_resp_rdata.value)
                response = (packed >> (64 * c)) & ((1 << 64) - 1)
                response_addr = (int(d.cpu_resp_addr.value) >> (32 * c)) & 0xFFFFFFFF
                response_write = (int(d.cpu_resp_write.value) >> c) & 1
                if response_addr != addr or response_write != int(write):
                    raise AssertionError(
                        f"core{c} response tag mismatch: addr={response_addr:#x}, "
                        f"write={response_write}, expected {addr:#x}/{int(write)}"
                    )
                d.cpu_resp_ready.value = self.mask
                await ClockCycles(d, 1)
                d.cpu_resp_ready.value = 0
                return response
        raise TimeoutError(
            f"core{c} response was not returned for {addr:#x}; "
            f"valid={int(d.cpu_resp_valid.value):b}, "
            f"protocol_error={int(d.protocol_error.value)}"
        )
