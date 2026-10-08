"""Small, tool-independent functional coverage collector.

This is intentionally separate from Verilator line coverage.  Verilator tells
us which RTL statements executed; this collector records whether verification
scenarios (hit/miss/MMIO/probe/backpressure) occurred.
"""

from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class CacheCoverage:
    """Transaction coverage bins and counters.

    Sampling is optional, so existing tests remain valid while new monitors can
    call ``sample_*`` without depending on pytest or Toffee internals.
    """

    bins: Counter = field(default_factory=Counter)
    transactions: int = 0

    def sample(self, **features):
        """Record a cross of named feature values, e.g. hit x mmio x stall."""
        self.transactions += 1
        for name, value in features.items():
            self.bins[f"{name}={value}"] += 1
        if features:
            cross = ",".join(f"{k}={features[k]}" for k in sorted(features))
            self.bins[f"cross:{cross}"] += 1

    def write(self, transaction):
        """Monitor subscriber hook; classify basic transaction objects."""
        command = getattr(transaction, "cmd", None)
        if command is not None:
            self.sample(command=command)

    def sample_request(self, command, result=None, mmio=False, backpressure=False):
        self.sample(command=command, result=result or "unknown",
                    mmio=mmio, backpressure=backpressure)

    def sample_probe(self, result, released_beats=0):
        self.sample(command="probe", result=result,
                    released_beats=released_beats)

    def sample_burst(self, kind, beats, stalled=False):
        self.sample(command=kind, beats=beats, backpressure=stalled)

    def as_dict(self):
        return {"transactions": self.transactions, "bins": dict(self.bins)}

    def write_json(self, path="reports/functional_coverage.json"):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True))
        return output
