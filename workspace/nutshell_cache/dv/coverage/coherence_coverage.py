"""Transaction-driven MESI coverage for the Python reference model."""

from collections import Counter


class CoherenceCoverage:
    """Sample stimulus/model transactions rather than PASS strings in logs."""

    def __init__(self):
        self.features = Counter()
        self.cross_state_opcode_core_source = Counter()
        self.l1_evictions = 0
        self.l2_live_evictions = 0
        self.l2_dirty_owner_evictions = 0
        self.l2_shared_evictions = 0
        self._model_progress = {}

    def sample(self, transition):
        event = transition["event"]
        self.features[event] += 1
        if transition.get("l2_refill"):
            self.features[f"l2_refill_{transition['l2_refill']}"] += 1
        old = transition["old_state"][transition["core"]]
        owner_state = transition["old_state"][1 - transition["core"]]
        source = transition.get("data_source", "unknown")
        refill = transition.get("l2_refill") or "none"
        target = transition.get("snoop_target")
        target = f"core{target}" if target is not None else "none"
        beats = transition.get("line_transfer_beats", 0)
        self.cross_state_opcode_core_source[
            f"{old}:from_{owner_state}:{transition['op']}:"
            f"core{transition['core']}:"
            f"source_{source}:l2_{refill}:snoop_{target}:beats_{beats}"
        ] += 1

    def observe_model(self, model, start_index=None):
        """Accumulate only new model transitions and eviction events."""
        key = id(model)
        previous = self._model_progress.get(key)
        if previous is None or previous[0] is not model:
            previous = (model, 0, 0, 0)
        transition_cursor = previous[1] if start_index is None else start_index
        for transition in model.transitions[transition_cursor:]:
            self.sample(transition)
        self.l1_evictions += len(model.l1_evictions) - previous[2]
        new_l2_evictions = model.l2_evictions[previous[3]:]
        self.l2_live_evictions += len(new_l2_evictions)
        evicted_by_line = {}
        for eviction in new_l2_evictions:
            evicted_by_line.setdefault(eviction["line"], []).append(eviction)
        for evictions in evicted_by_line.values():
            if any(item["state"] == "M" for item in evictions):
                self.l2_dirty_owner_evictions += 1
            if ({item["core"] for item in evictions if item["state"] == "S"}
                    == {0, 1}):
                self.l2_shared_evictions += 1
        self.features["l1_eviction"] = self.l1_evictions
        self.features["l2_live_eviction"] = self.l2_live_evictions
        self.features["l2_live_victim_dirty_owner"] = self.l2_dirty_owner_evictions
        self.features["l2_live_victim_shared"] = self.l2_shared_evictions
        self._model_progress[key] = (model, len(model.transitions),
                                     len(model.l1_evictions),
                                     len(model.l2_evictions))

    def sample_external(self, event, count=1):
        """Sample a checked driver or memory-interface event."""
        if count < 0:
            raise ValueError("coverage event count cannot be negative")
        self.features[event] += count

    def sample_interleaving(self, key):
        """Record a concurrent case after its independent checker passes."""
        self.cross_state_opcode_core_source[f"interleaving:{key}"] += 1

    def require(self, *events):
        missing = [event for event in events if not self.features[event]]
        if missing:
            raise AssertionError(f"uncovered Python coherence bins: {missing}")

    def to_dict(self):
        return {
            "features": dict(sorted(self.features.items())),
            "l1_evictions": self.l1_evictions,
            "l2_live_evictions": self.l2_live_evictions,
            "l2_dirty_owner_evictions": self.l2_dirty_owner_evictions,
            "l2_shared_evictions": self.l2_shared_evictions,
            "cross_state_opcode_core_source": dict(
                sorted(self.cross_state_opcode_core_source.items())
            ),
        }
