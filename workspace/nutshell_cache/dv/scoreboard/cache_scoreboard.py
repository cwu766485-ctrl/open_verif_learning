"""In-order CPU request/response scoreboard against the reference memory."""

from collections import deque

from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
from dv.common.utils.cmd_code import (
    CMD_READ,
    CMD_READBST,
    CMD_PROBE,
    CMD_PROBEHIT,
    CMD_PROBEMISS,
    CMD_READLST,
    CMD_WRITE,
    CMD_WRITEBST,
    CMD_WRITELST,
)
from dv.models.reference import CacheReferenceModel


class CacheScoreboard:
    def __init__(self, reference=None):
        self.reference = reference or CacheReferenceModel()
        self.pending = deque()
        self.errors = []
        self.compared = 0
        self.reset_drops = 0
        self._writeback_before_refill = False
        self.pending_probes = deque()
        self.active_probe_release = None

    def write(self, transaction):
        if isinstance(transaction, SimpleBusRequest):
            addr = transaction.addr & ~0x7
            existed = addr in self.reference.data
            old_value = self.reference.data.get(addr, 0)
            expected = self.reference.predict(transaction)
            self.pending.append({
                "request": transaction,
                "expected": expected,
                "addr": addr,
                "existed": existed,
                "old_value": old_value,
                "cache_miss": False,
                "memory_requests": [],
                "response_index": 0,
            })
        elif isinstance(transaction, SimpleBusResponse):
            self._compare(transaction)

    def write_channel(self, channel, transaction):
        """Consume bus observations; backing-memory traffic proves a miss.

        The active testbench serializes CPU transactions except for explicit
        reset/probe overlap, so the oldest pending CPU request owns any
        observed cache-memory request. MMIO traffic is on a separate channel.
        """
        if channel == "cpu":
            self.write(transaction)
        elif channel == "memory" and self.pending:
            command = transaction.get("cmd") if isinstance(transaction, dict) else None
            if isinstance(transaction, dict):
                self.pending[0]["memory_requests"].append(dict(transaction))
            if command in (CMD_WRITE, CMD_WRITEBST, CMD_WRITELST):
                self.pending[0]["cache_miss"] = True
                self._writeback_before_refill = True
            elif command in (CMD_READ, CMD_READBST):
                if self._writeback_before_refill:
                    self._writeback_before_refill = False
                else:
                    # Match each clean refill to the oldest CPU transaction
                    # which has not yet produced an external-memory request.
                    for item in self.pending:
                        if not item["cache_miss"]:
                            item["cache_miss"] = True
                            break
        elif channel == "coherence":
            if isinstance(transaction, SimpleBusRequest) and transaction.cmd == CMD_PROBE:
                self.pending_probes.append({
                    "addr": transaction.addr,
                    "expected": self.reference.probe_release_data(transaction.addr),
                    "release_index": 0,
                })
            elif isinstance(transaction, SimpleBusResponse):
                self._compare_probe(transaction)

    def _compare_probe(self, actual):
        if actual.cmd in (CMD_PROBEHIT, CMD_PROBEMISS):
            if not self.pending_probes:
                self._fail(f"unexpected coherence response {actual}")
            probe = self.pending_probes.popleft()
            was_hit = actual.cmd == CMD_PROBEHIT
            self.reference.observe_probe(probe["addr"], was_hit)
            if was_hit:
                self.active_probe_release = probe
            return
        if self.active_probe_release is None:
            self._fail(f"unexpected coherence release beat {actual}")
        probe = self.active_probe_release
        index = probe["release_index"]
        expected_data = probe["expected"][index]
        if actual.rdata != expected_data:
            self._fail(
                f"probe release addr=0x{probe['addr']:08x} beat={index}: "
                f"expected 0x{expected_data:016x}, got 0x{actual.rdata:016x}"
            )
        probe["release_index"] += 1
        if actual.cmd == CMD_READLST:
            if probe["release_index"] != 8:
                self._fail(f"probe release ended after {probe['release_index']} beat(s), expected 8")
            self.active_probe_release = None
        elif probe["release_index"] >= 8:
            self._fail("probe release did not terminate with READLST on beat 8")

    def _compare(self, actual):
        if not self.pending:
            self._fail(f"unexpected response {actual}")
            return
        item = self.pending[0]
        request = item["request"]
        expected = item["expected"]
        if isinstance(expected, list):
            expected = expected[item["response_index"]]
        self.compared += 1
        if actual.cmd != expected.cmd or actual.rdata != expected.rdata:
            self._fail(
                f"#{self.compared} addr=0x{request.addr:08x} cmd=0x{request.cmd:x}: "
                f"expected cmd=0x{expected.cmd:x}, data=0x{expected.rdata:016x}; "
                f"got cmd=0x{actual.cmd:x}, data=0x{actual.rdata:016x}"
            )
        if isinstance(item["expected"], list):
            item["response_index"] += 1
            if item["response_index"] < len(item["expected"]):
                return
        self.pending.popleft()
        if not self.reference.is_mmio(request.addr):
            self._check_cache_outcome(item)
        self.reference.observe_cache_access(request, item["cache_miss"])

    def _check_cache_outcome(self, item):
        request = item["request"]
        observed_miss = item["cache_miss"]
        prediction = self.reference.cache_tags.predict_access(request)
        if prediction.outcome == "hit" and observed_miss:
            self._fail(
                f"tag model predicted hit at 0x{request.addr:08x}, but cache issued "
                "a backing-memory request"
            )
        if prediction.outcome == "miss" and not observed_miss:
            self._fail(
                f"tag model predicted miss at 0x{request.addr:08x}, but no backing-memory "
                "request was observed"
            )

        resolved = self.reference.cache_tags.predict_access(request, was_miss=observed_miss)
        self._check_dirty_writeback(item, resolved)

    def _check_dirty_writeback(self, item, prediction):
        writebacks = [
            req for req in item["memory_requests"]
            if req.get("cmd") in (CMD_WRITEBST, CMD_WRITELST)
        ]
        if not writebacks:
            if prediction.dirty_victim_required:
                self._fail(
                    f"dirty victim required for miss at 0x{item['request'].addr:08x}, "
                    "but no writeback was observed"
                )
            return
        if len(writebacks) != 8:
            self._fail(f"dirty writeback had {len(writebacks)} beats, expected 8")

        line_base = writebacks[0].get("addr", -1) & ~0x3F
        if line_base not in prediction.dirty_victims:
            allowed = ", ".join(f"0x{addr:08x}" for addr in sorted(prediction.dirty_victims)) or "none"
            self._fail(
                f"unexpected dirty victim 0x{line_base:08x}; model allows: {allowed}"
            )

        for beat, req in enumerate(writebacks):
            # SimpleBus burst beats carry the line base on every request;
            # beat position advances implicitly at the memory controller.
            expected_addr = line_base
            expected_data_addr = line_base + beat * 8
            expected_cmd = CMD_WRITELST if beat == 7 else CMD_WRITEBST
            expected_data = self.reference.data.get(expected_data_addr, 0)
            if req.get("addr") != expected_addr:
                self._fail(
                    f"writeback beat {beat}: expected addr 0x{expected_addr:08x}, "
                    f"got 0x{req.get('addr', 0):08x}"
                )
            if req.get("cmd") != expected_cmd:
                self._fail(
                    f"writeback beat {beat}: expected cmd 0x{expected_cmd:x}, "
                    f"got 0x{req.get('cmd', -1):x}"
                )
            if req.get("wmask") != 0xFF:
                self._fail(
                    f"writeback beat {beat}: expected full byte mask 0xff, "
                    f"got 0x{req.get('wmask', 0):02x}"
                )
            if req.get("wdata") != expected_data:
                self._fail(
                    f"writeback beat {beat} at 0x{expected_data_addr:08x}: expected "
                    f"0x{expected_data:016x}, got 0x{req.get('wdata', 0):016x}"
                )

    def on_reset(self):
        """Flush transactions explicitly canceled by a synchronous DUT reset."""
        self.reset_drops += len(self.pending)
        # Predictions are applied at request acceptance so subsequent queued
        # reads see earlier writes. Roll back unretired writes in reverse order.
        for item in reversed(self.pending):
            request = item["request"]
            addr = item["addr"]
            existed = item["existed"]
            old_value = item["old_value"]
            if request.cmd == CMD_WRITE:
                if existed:
                    self.reference.data[addr] = old_value
                else:
                    self.reference.data.pop(addr, None)
        self.pending.clear()
        self._writeback_before_refill = False
        self.pending_probes.clear()
        self.active_probe_release = None
        self.reference.reset_cache_state()

    def _fail(self, message):
        self.errors.append(message)
        raise AssertionError("scoreboard: " + message)

    def assert_no_errors(self):
        assert not self.errors, "scoreboard errors: " + repr(self.errors)
        assert not self.pending, f"scoreboard has {len(self.pending)} unmatched request(s)"
        assert not self.pending_probes, f"scoreboard has {len(self.pending_probes)} unmatched probe(s)"
        assert self.active_probe_release is None, "scoreboard has an incomplete probe release"
