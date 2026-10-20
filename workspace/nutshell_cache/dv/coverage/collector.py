"""Monitor-driven functional coverage and mergeable JSON reporting."""

from collections import Counter, deque
from dataclasses import dataclass, field
import json
from pathlib import Path

from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
from dv.common.utils.cmd_code import (
    CMD_PROBE, CMD_PROBEHIT, CMD_PROBEMISS, CMD_READBST, CMD_READLST,
    CMD_WRITEBST, CMD_WRITE, CMD_READ,
)
from dv.models.reference import CacheReferenceModel


@dataclass
class CacheCoverage:
    bins: Counter = field(default_factory=Counter)
    transactions: int = 0
    _cpu_pending: deque = field(default_factory=deque, repr=False)
    _probe_releasing: bool = False
    _probe_release_beats: int = 0
    _mem_refills: int = 0
    _mem_writebacks: int = 0
    _last_cpu_addr: int | None = None

    GOALS = (
        "op=read", "op=write", "result=hit", "result=miss", "result=mmio",
        "probe=result=hit", "probe=result=miss", "burst=refill_beats=8",
        "burst=writeback_beats=8", "mask=full", "mask=partial",
        "backpressure=observed",
        "op_result=read/hit", "op_result=read/miss",
        "op_result=write/hit", "op_result=write/miss",
        "mask_result=partial/hit", "mask_result=partial/miss",
        "victim=dirty_eviction", "reset=cancelled_request",
        "set_occupancy=empty", "set_occupancy=one", "set_occupancy=two",
        "set_occupancy=three", "set_occupancy=full",
        "occupancy_result=empty/miss", "occupancy_result=partial/miss",
        "occupancy_result=full/miss", "occupancy_result=full/hit",
        "victim=clean_eviction", "partial_write=hit", "partial_write=miss",
        "backpressure_channel=cpu.req", "backpressure_channel=cpu.rsp",
        "probe_release=8_beats", "reset=cancelled_miss",
        "data_forwarding=same_word",
        "region=cache", "region=mmio",
        "op_result=read/mmio", "op_result=write/mmio",
        "line_boundary=adjacent_pair",
        "cross:result=miss,victim=dirty_eviction",
        "backpressure_channel=memory.req",
        "backpressure_channel=mmio.req",
        "arbitration=coherence_wins_cpu",
        "probe_way=0", "probe_way=1", "probe_way=2", "probe_way=3",
        "reset=cancelled_probe_release",
        "probe_sequence=consecutive",
        "probe_post_state=retained_hit",
    )

    MEGA_RANDOM_GOALS = (
        "region=cache", "region=mmio",
        "result=hit", "result=miss", "result=mmio",
        "op_result=read/hit", "op_result=read/miss", "op_result=read/mmio",
        "op_result=write/hit", "op_result=write/miss", "op_result=write/mmio",
        "mask_result=partial/hit", "mask_result=partial/miss",
        "burst=refill_beats=8", "burst=writeback_beats=8",
        "victim=clean_eviction", "victim=dirty_eviction",
        "set_occupancy=empty", "set_occupancy=one", "set_occupancy=two",
        "set_occupancy=three", "set_occupancy=full",
        "occupancy_result=full/hit", "occupancy_result=full/miss",
        "line_boundary=adjacent_pair",
        "cross:result=miss,victim=dirty_eviction",
    )

    def sample(self, **features):
        for name, value in features.items():
            self.bins[f"{name}={value}"] += 1
        if features:
            key = ",".join(f"{k}={features[k]}" for k in sorted(features))
            self.bins[f"cross:{key}"] += 1

    def write(self, transaction):
        self.write_channel("unknown", transaction)

    def write_channel(self, channel, transaction):
        if channel == "cpu":
            if isinstance(transaction, SimpleBusRequest):
                self._cpu_request(transaction)
            elif isinstance(transaction, SimpleBusResponse):
                self._cpu_response(transaction)
            return

        if channel == "coherence":
            if isinstance(transaction, SimpleBusRequest) and transaction.cmd == CMD_PROBE:
                self.transactions += 1
                self.sample(op="probe")
            elif isinstance(transaction, SimpleBusResponse):
                self._probe_response(transaction)
            return

        if channel in ("memory", "mmio") and isinstance(transaction, dict):
            self.transactions += 1
            command = transaction.get("cmd")
            size = transaction.get("size", 0)
            if channel == "memory":
                if command in (CMD_READBST, CMD_READ):
                    self._mem_refills += 1
                    self.sample_burst("refill", 1 << size)
                elif command == CMD_WRITEBST:
                    self._mem_writebacks += 1
                    self.sample_burst("writeback", 1 << size)
            elif channel == "mmio":
                self.sample(mmio_port="access")

    def _cpu_request(self, request):
        self.transactions += 1
        is_mmio = CacheReferenceModel.is_mmio(request.addr)
        self.sample(region="mmio" if is_mmio else "cache")
        previous_addr = self._last_cpu_addr
        if (
            previous_addr is not None
            and not is_mmio
            and not CacheReferenceModel.is_mmio(previous_addr)
            and (previous_addr & 0x3F) == 0x38
            and request.addr == previous_addr + 8
        ):
            self.sample(line_boundary="adjacent_pair")
        self._last_cpu_addr = request.addr

        if request.cmd == CMD_READ:
            op = "read"
        elif request.cmd == CMD_WRITE:
            op = "write"
        else:
            self.sample(op=f"cmd_{request.cmd:x}")
            return
        self.sample(op=op)
        if op == "write":
            if request.wmask == 0xFF:
                self.sample(mask="full")
            elif request.wmask not in (0,):
                self.sample(mask="partial")
            elif request.wmask == 0:
                self.sample(mask="zero")
        self._cpu_pending.append({
            "request": request,
            "operation": op,
            "mask_class": "full" if request.wmask == 0xFF else (
                "partial" if request.wmask else None
            ),
            "refills": self._mem_refills,
            "writebacks": self._mem_writebacks,
            "is_mmio": is_mmio,
            "responses_left": (1 << request.size) if request.cmd == CMD_READBST else 1,
        })

    def _cpu_response(self, _response):
        if not self._cpu_pending:
            self.sample(result="orphan_response")
            return
        item = self._cpu_pending[0]
        item["responses_left"] -= 1
        if item["responses_left"]:
            return
        self._cpu_pending.popleft()
        mem_refills, is_mmio = item["refills"], item["is_mmio"]
        if is_mmio:
            result = "mmio"
        elif self._mem_refills > mem_refills:
            result = "miss"
        else:
            result = "hit"
        self.sample(result=result, op_result=f"{item['operation']}/{result}")
        if item["mask_class"] == "partial":
            self.sample(mask_result=f"partial/{result}")
        if self._mem_writebacks > item["writebacks"]:
            self.sample(victim="dirty_eviction")

    def _probe_response(self, response):
        if response.cmd == CMD_PROBEHIT:
            self.bins["probe=result=hit"] += 1
            self.sample(probe="hit")
            self._probe_releasing = True
            self._probe_release_beats = 0
        elif response.cmd == CMD_PROBEMISS:
            self.bins["probe=result=miss"] += 1
            self.sample(probe="miss")
            self._probe_releasing = False
            self._probe_release_beats = 0
        elif self._probe_releasing:
            self._probe_release_beats += 1
            if response.cmd == CMD_READLST or self._probe_release_beats == 8:
                self.sample_burst("probe_release", self._probe_release_beats)
                if self._probe_release_beats == 8:
                    self.sample(probe_release="8_beats")
                self._probe_releasing = False

    def sample_request(self, command, result=None, mmio=False, backpressure=False):
        self.sample(command=command, result=result or "unknown", mmio=mmio,
                    backpressure=backpressure)

    def sample_probe(self, result, released_beats=0):
        self.sample(command="probe", result=result, released_beats=released_beats)

    def sample_burst(self, kind, beats, stalled=False):
        self.bins[f"burst={kind}_beats={beats}"] += 1
        self.sample(burst=kind, beats=beats, backpressure=stalled)

    def add_protocol_stalls(self, stall_counts):
        total = sum(stall_counts.values())
        if total:
            self.sample(backpressure="observed")
            for channel, cycles in sorted(stall_counts.items()):
                self.sample(backpressure_channel=channel, stall_cycles=cycles)

    def on_reset(self):
        cancelled = len(self._cpu_pending)
        cancelled_misses = sum(
            self._mem_refills > item["refills"] or self._mem_writebacks > item["writebacks"]
            for item in self._cpu_pending
        )
        self._cpu_pending.clear()
        self._probe_releasing = False
        self._probe_release_beats = 0
        self._last_cpu_addr = None
        if cancelled:
            self.sample(reset_cancelled_requests=cancelled)
            self.sample(reset="cancelled_request")
        if cancelled_misses:
            self.sample(reset_cancelled_misses=cancelled_misses)
            self.sample(reset="cancelled_miss")

    def sample_cache_access(self, *, occupancy, result, partial_write=False,
                            victim_class=None):
        occupancy_names = {0: "empty", 1: "one", 2: "two", 3: "three", 4: "full"}
        name = occupancy_names.get(occupancy, "ambiguous")
        self.sample(set_occupancy=name)
        if name in ("empty", "full") or result == "hit":
            self.sample(occupancy_result=f"{name}/{result}")
        elif name in ("one", "two", "three") and result == "miss":
            self.sample(occupancy_result="partial/miss")
        if partial_write:
            self.sample(partial_write=result)
        if victim_class is not None:
            victim = f"{victim_class}_eviction"
            self.sample(victim=victim)
            self.sample(result=result, victim=victim)

    def assert_clean(self):
        assert not self._cpu_pending, f"coverage collector has {len(self._cpu_pending)} unmatched CPU request(s)"
        assert not self._probe_releasing, "coverage collector has an incomplete probe release"

    def as_dict(self):
        hits = sum(1 for goal in self.GOALS if self.bins.get(goal, 0))
        total = len(self.GOALS)
        return {
            "transactions": self.transactions,
            "bins": dict(self.bins),
            "functional_coverage": {
                "covered_goals": hits,
                "total_goals": total,
                "percent": round(100.0 * hits / total, 1),
                "uncovered": [goal for goal in self.GOALS if not self.bins.get(goal, 0)],
            },
        }

    def write_json(self, path="reports/functional_coverage.json"):
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True))
        return out

    @staticmethod
    def merge_payloads(payloads):
        bins = Counter()
        transactions = 0
        for payload in payloads:
            bins.update(payload.get("bins", {}))
            transactions += payload.get("transactions", 0)
        hits = sum(1 for goal in CacheCoverage.GOALS if bins.get(goal, 0))
        total = len(CacheCoverage.GOALS)
        return {
            "transactions": transactions,
            "bins": dict(bins),
            "functional_coverage": {
                "covered_goals": hits,
                "total_goals": total,
                "percent": round(100.0 * hits / total, 1),
                "uncovered": [goal for goal in CacheCoverage.GOALS if not bins.get(goal, 0)],
            },
        }
