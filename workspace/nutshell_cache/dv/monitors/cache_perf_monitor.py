"""Sample public performance event pins from the coherent cache subsystem."""

from collections import Counter
from dataclasses import dataclass, asdict

from toffee import ClockCycles


@dataclass
class PerfCounts:
    cycles: int = 0
    l1_hit_core0: int = 0
    l1_miss_core0: int = 0
    l1_hit_core1: int = 0
    l1_miss_core1: int = 0
    l1_read_hit_core0: int = 0
    l1_read_miss_core0: int = 0
    l1_write_hit_core0: int = 0
    l1_write_miss_core0: int = 0
    l1_read_hit_core1: int = 0
    l1_read_miss_core1: int = 0
    l1_write_hit_core1: int = 0
    l1_write_miss_core1: int = 0
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
            "l1_hits": [],
            "directory_accepts": [],
            "directory_requests": [],
            "l2_lookups": [],
            "directory_grants": [],
        }
        self.stall_cycles = Counter()
        self.mshr_occupancy_histogram = Counter()
        self.directory_context_histogram = Counter()
        self.peak_mshr_occupancy = 0
        self.peak_directory_contexts = 0

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
                    "write": (int(d.cpu_req_write.value) >> core) & 1,
                })
            if int(d.perf_hit_event.value) & (1 << core):
                self.events["l1_hits"].append({
                    "cycle": cycle,
                    "addr": ((packed_addr >> (32 * core)) & 0xFFFFFFC0),
                    "core": core,
                    "write": (int(d.cpu_req_write.value) >> core) & 1,
                })
        if int(d.monitor_dir_req_accept_valid.value):
            self.events["directory_accepts"].append({
                "cycle": cycle,
                "addr": int(d.monitor_dir_req_accept_addr.value) & 0xFFFFFFC0,
            })
            self.events["directory_requests"].append({
                "cycle": cycle,
                "addr": int(d.monitor_dir_req_accept_addr.value) & 0xFFFFFFC0,
                "core": int(d.monitor_dir_req_accept_src_id.value),
                "opcode": int(d.monitor_dir_req_accept_opcode.value),
                "txn": int(d.monitor_dir_req_accept_txn_id.value),
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
                req_write = int(d.cpu_req_write.value)
                snoops = int(d.perf_snoop_event.value)
                self.counts.l1_hit_core0 += hits & 1
                self.counts.l1_hit_core1 += (hits >> 1) & 1
                self.counts.l1_miss_core0 += misses & 1
                self.counts.l1_miss_core1 += (misses >> 1) & 1
                self.counts.l2_refill_hit += int(d.perf_l2_refill_hit_event.value)
                self.counts.l2_refill_miss += int(d.perf_l2_refill_miss_event.value)
                self.counts.snoops += snoops.bit_count()
                self.counts.dirty_writebacks += int(d.perf_dirty_writeback_event.value)
                for core in range(2):
                    bit = 1 << core
                    if hits & bit:
                        kind = "write" if req_write & bit else "read"
                        field = f"l1_{kind}_hit_core{core}"
                        setattr(self.counts, field, getattr(self.counts, field) + 1)
                    if misses & bit:
                        kind = "write" if req_write & bit else "read"
                        field = f"l1_{kind}_miss_core{core}"
                        setattr(self.counts, field, getattr(self.counts, field) + 1)
                req_valid = int(d.cpu_req_valid.value)
                req_ready = int(d.cpu_req_ready.value)
                resp_valid = int(d.cpu_resp_valid.value)
                resp_ready = int(d.cpu_resp_ready.value)
                for core in range(2):
                    bit = 1 << core
                    if (req_valid & bit) and not (req_ready & bit):
                        self.stall_cycles[f"cpu_req_core{core}"] += 1
                    if (resp_valid & bit) and not (resp_ready & bit):
                        self.stall_cycles[f"cpu_resp_core{core}"] += 1

                for signal, ready, name in (
                    (d.mem_rd_req_valid, d.mem_rd_req_ready, "mem_read_req"),
                    (d.mem_rd_data_valid, d.mem_rd_data_ready, "mem_read_data"),
                    (d.mem_wr_req_valid, d.mem_wr_req_ready, "mem_write_req"),
                    (d.mem_wr_data_valid, d.mem_wr_data_ready, "mem_write_data"),
                    (d.mem_wr_rsp_valid, d.mem_wr_rsp_ready, "mem_write_rsp"),
                    (d.monitor_dir_req_live_valid, d.monitor_dir_req_live_ready,
                     "directory_req"),
                    (d.monitor_dir_xfer_live_valid, d.monitor_dir_xfer_live_ready,
                     "directory_transfer"),
                ):
                    if int(signal.value) and not int(ready.value):
                        self.stall_cycles[name] += 1
                snoop_valid = int(d.monitor_snoop_offer_valid.value)
                snoop_ready = int(d.monitor_snoop_offer_ready.value)
                for core in range(2):
                    if (snoop_valid & (1 << core)) and not (snoop_ready & (1 << core)):
                        self.stall_cycles[f"snoop_core{core}"] += 1

                mshr_occupancy = int(d.monitor_mem_mshr_valid.value).bit_count()
                directory_occupancy = int(
                    d.monitor_directory_active_contexts.value
                ).bit_count()
                self.mshr_occupancy_histogram[mshr_occupancy] += 1
                self.directory_context_histogram[directory_occupancy] += 1
                self.peak_mshr_occupancy = max(self.peak_mshr_occupancy,
                                               mshr_occupancy)
                self.peak_directory_contexts = max(self.peak_directory_contexts,
                                                   directory_occupancy)
            await ClockCycles(d, 1)
            self.counts.cycles += 1

    def snapshot(self):
        return self.counts.snapshot()

    def extended_snapshot(self):
        """Return event cursors and resource counters for workload windows."""
        return {
            "events": self.event_snapshot(),
            "stall_cycles": dict(self.stall_cycles),
            "mshr_occupancy_histogram": dict(self.mshr_occupancy_histogram),
            "directory_context_histogram": dict(self.directory_context_histogram),
            "peak_mshr_occupancy": self.peak_mshr_occupancy,
            "peak_directory_contexts": self.peak_directory_contexts,
        }
