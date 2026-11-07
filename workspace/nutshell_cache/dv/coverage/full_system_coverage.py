"""Checked event coverage for the first integrated-top verification slice.

The collector accepts only events observed at DUT handshakes or metadata
commit probes after the full-system checker has passed. It does not synthesize
RTL events from the reference model.
"""

from collections import Counter


class FullSystemCoverage:
    def __init__(self):
        self.bins = Counter()
        self.cross = Counter()
        self.test_id = None
        self.bin_testcases = {}
        self.cross_testcases = {}
        self.checked_cross_evidence = {}

    def set_testcase(self, test_id):
        """Bind later checked samples to the pytest testcase that made them."""
        self.test_id = str(test_id)

    def _record_testcase(self, table, point_id):
        if self.test_id:
            table.setdefault(point_id, set()).add(self.test_id)

    def sample_checked_cpu(self, core, write, accepted, completed):
        if not (accepted and completed):
            raise AssertionError("CPU coverage requires accepted and completed request")
        op = "WRITE" if write else "READ"
        self.bins[f"FS.CPU.{op}.CORE{core}"] += 1
        self.cross[f"FS.CROSS.CORE{core}.{op}"] += 1
        self._record_testcase(self.bin_testcases, f"FS.CPU.{op}.CORE{core}")
        self._record_testcase(self.cross_testcases, f"FS.CROSS.CORE{core}.{op}")

    def sample_checked_event(self, event_id, *, checked):
        if not checked:
            raise AssertionError(f"coverage event {event_id} lacks a passing checker")
        self.bins[event_id] += 1
        self._record_testcase(self.bin_testcases, event_id)

    def sample_checked_cross(self, cross_id, *, checked, evidence=None):
        if not checked:
            raise AssertionError(f"cross {cross_id} lacks a passing checker")
        if evidence is not None:
            if not evidence.get("checker_pass") or not evidence.get("overlap"):
                raise AssertionError(f"cross {cross_id} has invalid overlap evidence")
            self.checked_cross_evidence.setdefault(cross_id, []).append(evidence)
        self.cross[cross_id] += 1
        self._record_testcase(self.cross_testcases, cross_id)

    def report(self):
        return {
            "bins": dict(sorted(self.bins.items())),
            "cross_bins": dict(sorted(self.cross.items())),
            # These are exact pytest node IDs that sampled the point. Checker
            # identity is declared in the plan; this field must not imply that
            # the runtime collector introspects Python assertion execution.
            "sample_testcases": {
                "bins": {key: sorted(value) for key, value in
                         sorted(self.bin_testcases.items())},
                "cross_bins": {key: sorted(value) for key, value in
                               sorted(self.cross_testcases.items())},
            },
            "checked_cross_evidence": {
                key: list(value) for key, value in
                sorted(self.checked_cross_evidence.items())
            },
        }
