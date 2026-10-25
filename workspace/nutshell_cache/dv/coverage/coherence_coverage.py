"""Transaction-driven MESI coverage for the Python reference model."""

from collections import Counter


class CoherenceCoverage:
    """Sample stimulus/model transactions rather than PASS strings in logs."""

    def __init__(self):
        self.features = Counter()
        self.cross_state_opcode_core_source = Counter()
        self.l1_evictions = 0
        self.l2_live_evictions = 0

    def sample(self, transition):
        event = transition["event"]
        self.features[event] += 1
        if transition.get("l2_refill"):
            self.features[f"l2_refill_{transition['l2_refill']}"] += 1
        old = transition["old_state"][transition["core"]]
        self.cross_state_opcode_core_source[
            f"{old}:{transition['op']}:core{transition['core']}:{event}"
        ] += 1
        if transition.get("l2_refill"):
            self.cross_state_opcode_core_source[
                f"{old}:{transition['op']}:core{transition['core']}:"
                f"l2_{transition['l2_refill']}"
            ] += 1

    def observe_model(self, model, start_index=0):
        for transition in model.transitions[start_index:]:
            self.sample(transition)
        self.l1_evictions = len(model.l1_evictions)
        self.l2_live_evictions = len(model.l2_evictions)
        self.features["l1_eviction"] = self.l1_evictions
        self.features["l2_live_eviction"] = self.l2_live_evictions

    def sample_external(self, event, count=1):
        """Sample a checked driver or memory-interface event."""
        if count < 0:
            raise ValueError("coverage event count cannot be negative")
        self.features[event] += count

    def require(self, *events):
        missing = [event for event in events if not self.features[event]]
        if missing:
            raise AssertionError(f"uncovered Python coherence bins: {missing}")

    def to_dict(self):
        return {
            "features": dict(sorted(self.features.items())),
            "l1_evictions": self.l1_evictions,
            "l2_live_evictions": self.l2_live_evictions,
            "cross_state_opcode_core_source": dict(
                sorted(self.cross_state_opcode_core_source.items())
            ),
        }
