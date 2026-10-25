"""Small independent two-core MESI/data model used by Python subsystem DV."""

from collections import defaultdict


class CoherenceScoreboard:
    def __init__(self):
        self.states = defaultdict(lambda: ["I", "I"])
        self.data = {}
        self.events = set()

    def seed_word(self, addr: int, value: int):
        self.data[addr] = value & ((1 << 64) - 1)

    def predict(self, core: int, addr: int, *, write: bool = False,
                 write_data: int = 0):
        line = addr & ~0x3F
        own, other = self.states[line][core], self.states[line][1 - core]
        current = self.data.get(addr, 0)
        if write:
            if own == "S":
                event = "shared_upgrade"
            elif own in ("E", "M"):
                event = "write_hit"
            else:
                event = "cold_write"
            return current, event

        if own != "I":
            event = "read_hit"
        elif other == "M":
            event = "remote_read_from_M"
        elif other == "E":
            event = "remote_read_from_E"
        elif other == "S":
            event = "remote_read_from_S"
        else:
            event = "cold_read"
        return current, event

    def observe(self, core: int, addr: int, *, write: bool = False,
                write_data: int = 0, response_data: int = 0):
        line = addr & ~0x3F
        own, other = self.states[line][core], self.states[line][1 - core]
        expected, event = self.predict(core, addr, write=write,
                                       write_data=write_data)
        if not write and response_data != expected:
            raise AssertionError(
                f"core{core} read {addr:#x}: got {response_data:#018x}, "
                f"expected {expected:#018x} ({event})"
            )

        if write:
            self.states[line][core] = "M"
            self.states[line][1 - core] = "I"
            self.data[addr] = write_data & ((1 << 64) - 1)
        elif own == "I":
            if other == "I":
                self.states[line][core] = "E"
            else:
                self.states[line][core] = "S"
                if other in ("E", "M"):
                    self.states[line][1 - core] = "S"
        self.events.add(event)
        return expected, event

    def assert_covered(self, *required_events):
        missing = sorted(set(required_events) - self.events)
        if missing:
            raise AssertionError(f"coherence functional bins not hit: {missing}")
