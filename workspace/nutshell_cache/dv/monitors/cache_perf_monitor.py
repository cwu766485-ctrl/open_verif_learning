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
        self.events = {
            "l1_misses": [],
            "directory_accepts": [],
            "l2_lookups": [],
            "directory_grants": [],
        }

    def event_snapshot(self):
        return {name: len(items) for name, items in self.events.items()}

    def events_since(self, snapshot):
        return {name: items[snapshot[name]:]
                for name, items in self.events.items()}

    def _sample_stage_events(self, d):
        cycle = self.counts.cycles
        miss = int(d.perf_miss_event.value)
        packed_addr = int(d.cpu_req_addr.value)
        for core in range(2):
            # perf_miss_event is generated from the accepted CPU request
            # handshake inside the cluster. Use that event as the authority;
            # wrapper-level ready sampling can observe a different delta phase.
            if miss & (1 << core):
                self.events["l1_misses"].append({
                    "cycle": cycle,
                    "addr": ((packed_addr >> (32 * core)) & 0xFFFFFFC0),
                    "core": core,
                })
        if int(d.monitor_dir_req_accept_valid.value):
            self.events["directory_accepts"].append({
                "cycle": cycle,
                "addr": int(d.monitor_dir_req_accept_addr.value) & 0xFFFFFFC0,
            })
        if int(d.monitor_l2_lookup_valid.value):
            self.events["l2_lookups"].append({
                "cycle": cycle,
                "addr": int(d.monitor_l2_lookup_addr.value) & 0xFFFFFFC0,
                "hit": int(d.monitor_l2_lookup_hit.value),
            })
        if int(d.monitor_dir_grant_accept_valid.value):
            self.events["directory_grants"].append({
                "cycle": cycle,
                "addr": int(d.monitor_dir_grant_accept_addr.value) & 0xFFFFFFC0,
            })

    async def run(self):
        d = self.dut
        while True:
            if not int(d.reset.value):
                self._sample_stage_events(d)
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
            await ClockCycles(d, 1)
            self.counts.cycles += 1

    def snapshot(self):
        return self.counts.snapshot()
