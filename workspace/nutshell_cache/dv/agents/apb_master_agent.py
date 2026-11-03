"""APB3 master driver for the cache performance CSR window."""

from toffee import ClockCycles


class ApbMasterAgent:
    CSR_HIT_COUNT = 0x00
    CSR_MISS_COUNT = 0x04
    CSR_SNOOP_COUNT = 0x08
    CSR_DIRTY_WRITEBACK_COUNT = 0x0C
    CSR_ERROR_STATUS = 0x10
    CSR_ACCESS_CYCLES = 0x14
    CSR_COMPLETED_ACCESSES = 0x18

    def __init__(self, dut, *, max_wait_cycles=32):
        self.dut = dut
        self.max_wait_cycles = max_wait_cycles
        self.cycle = 0
        self.transactions = []
        self.observation_callback = None

    async def access(self, addr, *, write=False, data=0):
        d = self.dut
        d.apb_psel.value = 0
        d.apb_penable.value = 0
        d.apb_pwrite.value = int(write)
        d.apb_paddr.value = addr & 0xFFFF_FFFF
        # APB setup phase.
        d.apb_psel.value = 1
        await ClockCycles(d, 1)
        self.cycle += 1
        # APB access phase. Payload remains unchanged until completion.
        d.apb_penable.value = 1
        for _ in range(self.max_wait_cycles):
            await ClockCycles(d, 1)
            self.cycle += 1
            if int(d.apb_pready.value):
                result = {
                    "addr": addr & 0xFFFF_FFFF,
                    "write": int(write),
                    "data": data & 0xFFFF_FFFF,
                    "rdata": int(d.apb_prdata.value),
                    "slverr": int(d.apb_pslverr.value),
                    "cycle": self.cycle,
                }
                self.transactions.append(result)
                if self.observation_callback is not None:
                    self.observation_callback(result)
                d.apb_psel.value = 0
                d.apb_penable.value = 0
                d.apb_pwrite.value = 0
                d.apb_paddr.value = 0
                await ClockCycles(d, 1)
                self.cycle += 1
                return result
        d.apb_psel.value = 0
        d.apb_penable.value = 0
        raise TimeoutError(f"APB access timeout at {addr:#x}")

    async def read(self, addr):
        result = await self.access(addr)
        if result["slverr"]:
            raise AssertionError(f"APB read at {addr:#x} returned PSLVERR")
        return result["rdata"]

    async def write(self, addr, data=0):
        return await self.access(addr, write=True, data=data)
