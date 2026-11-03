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

    def sample_checked_cpu(self, core, write, accepted, completed):
        if not (accepted and completed):
            raise AssertionError("CPU coverage requires accepted and completed request")
        op = "WRITE" if write else "READ"
        self.bins[f"FS.CPU.{op}.CORE{core}"] += 1
        self.cross[f"FS.CROSS.CORE{core}.{op}"] += 1

    def sample_checked_event(self, event_id, *, checked):
        if not checked:
            raise AssertionError(f"coverage event {event_id} lacks a passing checker")
        self.bins[event_id] += 1

    def sample_checked_cross(self, cross_id, *, checked):
        if not checked:
            raise AssertionError(f"cross {cross_id} lacks a passing checker")
        self.cross[cross_id] += 1

    def report(self):
        return {"bins": dict(sorted(self.bins.items())),
                "cross_bins": dict(sorted(self.cross.items()))}
