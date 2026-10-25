"""Sample public performance event pins from the coherent cache subsystem."""

from dataclasses import dataclass, asdict

from toffee import ClockCycles


@dataclass
class PerfCounts:
    cycles: int = 0
    l1_hit_core0: int = 0
    l1_miss_core0: int = 0
    l1_hit_core1: int = 0
    l1_miss_core1: int = 0
    l2_refill_hit: int = 0
    l2_refill_miss: int = 0
    snoops: int = 0
    dirty_writebacks: int = 0

    def snapshot(self):
        return asdict(self)

    def __sub__(self, earlier):
        return PerfCounts(**{
            field: getattr(self, field) - getattr(earlier, field)
            for field in self.__dataclass_fields__
        })


class CachePerfMonitor:
    def __init__(self, dut):
        self.dut = dut
        self.counts = PerfCounts()

    async def run(self):
        d = self.dut
        while True:
            await ClockCycles(d, 1)
            self.counts.cycles += 1
            if int(d.reset.value):
                continue
            hits = int(d.perf_hit_event.value)
            misses = int(d.perf_miss_event.value)
            snoops = int(d.perf_snoop_event.value)
            self.counts.l1_hit_core0 += hits & 1
            self.counts.l1_hit_core1 += (hits >> 1) & 1
            self.counts.l1_miss_core0 += misses & 1
            self.counts.l1_miss_core1 += (misses >> 1) & 1
            self.counts.l2_refill_hit += int(d.perf_l2_refill_hit_event.value)
            self.counts.l2_refill_miss += int(d.perf_l2_refill_miss_event.value)
            self.counts.snoops += snoops.bit_count()
            self.counts.dirty_writebacks += int(d.perf_dirty_writeback_event.value)

    def snapshot(self):
        return self.counts.snapshot()
