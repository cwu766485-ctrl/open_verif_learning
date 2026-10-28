"""Check accepted owner-to-L2 line transfers at the subsystem boundary."""

from toffee import ClockCycles


class SnoopDataMonitor:
    """Collect complete eight-beat owner transfers accepted by the L2 write port."""

    BEATS_PER_LINE = 8

    def __init__(self, dut):
        self.dut = dut
        self.partial = {}
        self.transfers = []
        self.snoops = []
        self.victim_snoops = []
        self.snoop_response_cycles = []
        self.directory_snoop_response_cycles = []
        self.directory_commits = []
        self.directory_requests = []
        self.directory_grants = []
        self.l2_lookups = []
        self.lookup_conflicts = []
        self.transfer_grant_conflicts = []
        self.beat_errors = []
        self.shared_write_conflicts = []
        self.cycle = 0

    async def run(self):
        d = self.dut
        while True:
            # Observe the combinational accepted-beat event before the next
            # rising edge; state machines may deassert valid at that edge.
            snoop_valid = int(d.monitor_snoop_accept_valid.value)
            rsp_valid = int(d.monitor_snoop_rsp_valid.value)
            rsp_ready = int(d.monitor_snoop_rsp_ready.value)
            rsp_txn = int(d.monitor_snoop_rsp_txn_id.value)
            rsp_opcode = int(d.monitor_snoop_rsp_opcode.value)
            for core in range(2):
                bit = 1 << core
                if (rsp_valid | rsp_ready) & bit:
                    self.snoop_response_cycles.append({
                        "cycle": self.cycle, "core": core,
                        "valid": int(bool(rsp_valid & bit)),
                        "ready": int(bool(rsp_ready & bit)),
                        "fill": bool(int(d.monitor_l2_fill_active.value)),
                        "txn": (rsp_txn >> (3 * core)) & 0b111,
                        "opcode": (rsp_opcode >> (2 * core)) & 0b11,
                    })
            if (int(d.monitor_dir_snoop_rsp_valid.value) or
                    int(d.monitor_dir_snoop_rsp_ready.value)):
                self.directory_snoop_response_cycles.append({
                    "cycle": self.cycle,
                    "valid": int(d.monitor_dir_snoop_rsp_valid.value),
                    "ready": int(d.monitor_dir_snoop_rsp_ready.value),
                    "fill": bool(int(d.monitor_l2_fill_active.value)),
                    "target": int(d.monitor_dir_snoop_target.value),
                    "txn": int(d.monitor_dir_snoop_txn_id.value),
                    "opcode": int(d.monitor_dir_snoop_rsp_opcode.value),
                })
            for core in range(2):
                if snoop_valid & (1 << core):
                    self.snoops.append({
                        "core": core,
                        "line": (int(d.monitor_snoop_accept_addr.value) >> (32 * core)) &
                                0xFFFFFFC0,
                        "opcode": (int(d.monitor_snoop_accept_opcode.value) >> core) & 1,
                        "txn": (int(d.monitor_snoop_accept_txn_id.value) >>
                                (3 * core)) & 0b111,
                        "cycle": self.cycle,
                        "during_l2_fill": bool(int(d.monitor_l2_fill_active.value)),
                    })
            if int(d.monitor_victim_snoop_accept_valid.value):
                self.victim_snoops.append({
                    "core": int(d.monitor_victim_snoop_accept_core.value),
                    "line": int(d.monitor_victim_snoop_accept_addr.value) &
                            0xFFFFFFC0,
                    "cycle": self.cycle,
                })
            if int(d.monitor_dir_commit_valid.value):
                self.directory_commits.append({
                    "cycle": self.cycle,
                    "line": int(d.monitor_dir_commit_addr.value) & 0xFFFFFFC0,
                    "state": int(d.monitor_dir_commit_state.value),
                    "sharers": int(d.monitor_dir_commit_sharers.value),
                    "owner": int(d.monitor_dir_commit_owner.value),
                })
            if int(d.monitor_dir_req_accept_valid.value):
                self.directory_requests.append({
                    "line": int(d.monitor_dir_req_accept_addr.value) & 0xFFFFFFC0,
                    "core": int(d.monitor_dir_req_accept_src_id.value),
                    "opcode": int(d.monitor_dir_req_accept_opcode.value),
                    "txn": int(d.monitor_dir_req_accept_txn_id.value),
                    "cycle": self.cycle,
                })
            if int(d.monitor_l2_lookup_valid.value):
                self.l2_lookups.append({
                    "line": int(d.monitor_l2_lookup_addr.value) & 0xFFFFFFC0,
                    "hit": bool(int(d.monitor_l2_lookup_hit.value)),
                    "cycle": self.cycle,
                })
            if int(d.monitor_dir_grant_accept_valid.value):
                self.directory_grants.append({
                    "line": int(d.monitor_dir_grant_accept_addr.value) & 0xFFFFFFC0,
                    "dst": int(d.monitor_dir_grant_accept_dst.value),
                    "opcode": int(d.monitor_dir_grant_accept_opcode.value),
                    "txn": int(d.monitor_dir_grant_accept_txn_id.value),
                    "cycle": self.cycle,
                })
            if int(d.monitor_dir_lookup_conflict_valid.value):
                self.lookup_conflicts.append({
                    "incoming": int(d.monitor_dir_lookup_conflict_incoming_addr.value) &
                                0xFFFFFFC0,
                    "active": int(d.monitor_dir_lookup_conflict_active_addr.value) &
                              0xFFFFFFC0,
                    "active_kind": ("transfer" if int(
                        d.monitor_dir_lookup_conflict_is_transfer.value)
                                    else "grant"),
                })
            if int(d.monitor_dir_transfer_grant_conflict_valid.value):
                self.transfer_grant_conflicts.append({
                    "lookup": int(
                        d.monitor_dir_transfer_grant_conflict_lookup_addr.value
                    ) & 0xFFFFFFC0,
                    "grant": int(
                        d.monitor_dir_transfer_grant_conflict_grant_addr.value
                    ) & 0xFFFFFFC0,
                })
            if int(d.reset.value):
                await ClockCycles(d, 1)
                self.cycle += 1
                continue
            if int(d.monitor_owner_data_valid.value):
                core = int(d.monitor_owner_data_core.value)
                addr = int(d.monitor_owner_data_addr.value) & ~0x3F
                beat = int(d.monitor_owner_data_beat_idx.value)
                data = int(d.monitor_owner_data.value)
                last = int(d.monitor_owner_data_last.value)
                if int(d.monitor_l2_fill_active.value):
                    self.shared_write_conflicts.append({
                        "cycle": self.cycle, "core": core, "line": addr,
                        "beat": beat,
                    })
                key = (core, addr)
                words = self.partial.setdefault(key, [])
                expected_beat = len(words)
                if beat != expected_beat:
                    self.beat_errors.append({"core": core, "line": addr,
                                             "got": beat, "expected": expected_beat})
                    words.clear()
                if beat == len(words):
                    words.append(data)
                if last != int(beat == self.BEATS_PER_LINE - 1):
                    self.beat_errors.append({"core": core, "line": addr,
                                             "beat": beat, "last": last})
                if last:
                    self.transfers.append({"core": core, "line": addr,
                                           "words": tuple(words)})
                    del self.partial[key]
            await ClockCycles(d, 1)
            self.cycle += 1

    def assert_line_data(self, addr, expected_words, *, since=0):
        line = addr & ~0x3F
        expected = tuple(expected_words)
        matching = [item for item in self.transfers[since:]
                    if item["line"] == line]
        if self.beat_errors:
            raise AssertionError(f"malformed accepted snoop-data beats: {self.beat_errors}")
        if not matching:
            raise AssertionError(
                f"no accepted owner-data transfer observed for {line:#x}; "
                f"new transfers={self.transfers[since:]}, partial={self.partial}"
            )
        for transfer in matching:
            if transfer["words"] != expected:
                raise AssertionError(
                    f"owner-data transfer for {line:#x} from core{transfer['core']} "
                    f"was {[f'{word:#018x}' for word in transfer['words']]}, "
                    f"expected {[f'{word:#018x}' for word in expected]}"
                )

    def assert_directory_matches(self, model, addr):
        """Compare the latest accepted L2 directory commit with model state."""
        line = addr & ~0x3F
        commits = [item for item in self.directory_commits
                   if item["line"] == line]
        if not commits:
            raise AssertionError(f"no accepted directory metadata commit for {line:#x}")
        expected = model.directory_view(line)
        state_code = {"I": 0, "S": 1, "U": 2}[expected["state"]]
        expected_owner = expected["owner"] or 0
        observed = commits[-1]
        if (observed["state"] != state_code or
                observed["sharers"] != expected["sharers"] or
                observed["owner"] != expected_owner):
            raise AssertionError(
                f"directory metadata mismatch for {line:#x}: "
                f"observed={observed}, expected={expected}"
            )

    def assert_no_shared_write_conflict(self):
        if self.shared_write_conflicts:
            raise AssertionError(
                "L2 refill and owner-data write used the shared array port "
                f"in the same cycle: {self.shared_write_conflicts}"
            )
