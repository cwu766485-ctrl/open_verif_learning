"""Independent global MESI/data model for two L1s and a shared inclusive L2."""

from collections import Counter, defaultdict


WORD_MASK = (1 << 64) - 1


class CoherenceScoreboard:
    """Architectural model driven only by requests and accepted responses.

    This model does not inspect the DUT's computed MESI state. It tracks line
    permissions, byte-accurate architectural data, the implied directory
    owner/sharer set, and observed transaction classes.
    """

    def __init__(self):
        self.states = defaultdict(lambda: ["I", "I"])
        self.data = {}  # byte address -> 64-bit architectural word
        self.events = set()
        self.event_counts = Counter()
        self.transitions = []
        self.l1_ways = [defaultdict(lambda: [None] * 4) for _ in range(2)]
        self.l1_next_way = [defaultdict(int) for _ in range(2)]
        self.l2_ways = defaultdict(lambda: [None] * 8)
        self.l2_next_way = defaultdict(int)
        self.directory = {}
        self.l1_evictions = []
        self.l2_evictions = []
        self.track_l1_replacement = True

    def seed_word(self, addr: int, value: int):
        self.data[addr & ~0x7] = value & WORD_MASK

    def seed_line(self, addr: int, words):
        if len(words) != 8:
            raise ValueError("a cache line contains exactly eight 64-bit words")
        line = addr & ~0x3F
        for beat, value in enumerate(words):
            self.seed_word(line + 8 * beat, value)

    def word(self, addr: int) -> int:
        return self.data.get(addr & ~0x7, 0)

    def predict(self, core: int, addr: int, *, write: bool = False,
                write_data: int = 0, write_mask: int = 0xFF):
        if core not in (0, 1):
            raise ValueError("core must be 0 or 1")
        line = addr & ~0x3F
        own, other = self.states[line][core], self.states[line][1 - core]
        current = self.word(addr)
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

    @staticmethod
    def _merge_bytes(old: int, new: int, byte_mask: int) -> int:
        value = old
        for lane in range(8):
            if (byte_mask >> lane) & 1:
                mask = 0xFF << (8 * lane)
                value = (value & ~mask) | (new & mask)
        return value & WORD_MASK

    def directory_view(self, addr: int):
        """Return the directory state implied by modeled L1 copies."""
        copies = self.states[addr & ~0x3F]
        valid = [core for core, state in enumerate(copies) if state != "I"]
        modified = [core for core, state in enumerate(copies) if state == "M"]
        exclusive = [core for core, state in enumerate(copies) if state == "E"]
        if modified:
            return {"state": "U", "owner": modified[0], "sharers": 0}
        if exclusive:
            return {"state": "U", "owner": exclusive[0], "sharers": 0}
        if valid:
            return {"state": "S", "owner": None,
                    "sharers": sum(1 << core for core in valid)}
        return {"state": "I", "owner": None, "sharers": 0}

    @staticmethod
    def _l1_set(line: int) -> int:
        return (line >> 6) & 0x7F

    @staticmethod
    def _l2_set(line: int) -> int:
        return (line >> 6) & 0x1FF

    def l1_way_view(self, core: int, addr: int):
        """Return modeled way index, or ``None`` if the line is not resident."""
        line = addr & ~0x3F
        ways = self.l1_ways[core][self._l1_set(line)]
        return next((way for way, candidate in enumerate(ways)
                     if candidate == line), None)

    def l2_contains(self, addr: int) -> bool:
        line = addr & ~0x3F
        return line in self.l2_ways[self._l2_set(line)]

    def _remove_l1_copy(self, core: int, line: int):
        ways = self.l1_ways[core][self._l1_set(line)]
        for way, candidate in enumerate(ways):
            if candidate == line:
                ways[way] = None
                return

    def _touch_l2_write(self, line: int):
        """Model the replacement-pointer update on a full-line L2 data write."""
        set_index = self._l2_set(line)
        ways = self.l2_ways[set_index]
        if line in ways:
            way = ways.index(line)
            self.l2_next_way[set_index] = (way + 1) % 8

    def _allocate_l1(self, core: int, line: int):
        if not self.track_l1_replacement:
            return
        set_index = self._l1_set(line)
        ways = self.l1_ways[core][set_index]
        if line in ways:
            return
        free = [way for way, candidate in enumerate(ways) if candidate is None]
        if free:
            # The RTL's descending scan leaves the lowest numbered invalid way.
            way = min(free)
        else:
            way = self.l1_next_way[core][set_index] % 4
            victim = ways[way]
            victim_state = self.states[victim][core]
            if victim_state == "M":
                self._touch_l2_write(victim)
            self.states[victim][core] = "I"
            self.l1_evictions.append({"core": core, "line": victim,
                                      "state": victim_state,
                                      "states_after": tuple(self.states[victim]),
                                      "operation": getattr(self, "operation_index", None)})
            self.directory[victim] = self.directory_view(victim)
        ways[way] = line
        self.l1_next_way[core][set_index] = (way + 1) % 4

    def observe_l1_put(self, core: int, addr: int, opcode: int):
        """Apply a completed replacement observed on the Directory request port."""
        if core not in (0, 1):
            raise ValueError("core must be 0 or 1")
        if opcode not in (0b011, 0b100, 0b101):
            raise ValueError(f"not a Put request opcode: {opcode:#b}")
        line = addr & ~0x3F
        state = self.states[line][core]
        # A completed PutM returns a full dirty line to L2. The L2 array
        # advances its replacement pointer when that line write completes.
        if state == "M":
            self._touch_l2_write(line)
        self.states[line][core] = "I"
        self._remove_l1_copy(core, line)
        self.directory[line] = self.directory_view(line)
        self.l1_evictions.append({
            "core": core, "line": line, "state": state,
            "source": "directory_put",
        })

    def _ensure_l2_line(self, line: int) -> bool:
        """Ensure an inclusive L2 entry exists; return whether it was present."""
        set_index = self._l2_set(line)
        ways = self.l2_ways[set_index]
        if line in ways:
            return True
        free = [way for way, candidate in enumerate(ways) if candidate is None]
        if free:
            # SharedL2DirectoryArray's line-write scan chooses the highest free way.
            way = max(free)
        else:
            way = self.l2_next_way[set_index] % 8
            victim = ways[way]
            for core in range(2):
                if self.states[victim][core] != "I":
                    state = self.states[victim][core]
                    self.states[victim][core] = "I"
                    self._remove_l1_copy(core, victim)
                    self.l2_evictions.append({"line": victim, "core": core,
                                              "state": state})
            self.directory.pop(victim, None)
        ways[way] = line
        self.l2_next_way[set_index] = (way + 1) % 8
        self.directory.setdefault(line, {"state": "I", "owner": None,
                                         "sharers": 0})
        return False

    def _assert_line_invariants(self, line: int):
        copies = self.states[line]
        if copies.count("M") > 1 or copies.count("E") > 1:
            raise AssertionError(f"multiple exclusive owners on line {line:#x}: {copies}")
        if "M" in copies and sum(state != "I" for state in copies) != 1:
            raise AssertionError(f"M coexists with another copy on {line:#x}: {copies}")
        if "E" in copies and sum(state != "I" for state in copies) != 1:
            raise AssertionError(f"E coexists with another copy on {line:#x}: {copies}")
        if line in self.directory and self.directory[line] != self.directory_view(line):
            raise AssertionError(
                f"directory owner/sharers disagree with L1 model on {line:#x}: "
                f"{self.directory[line]} vs {self.directory_view(line)}"
            )

    def observe(self, core: int, addr: int, *, write: bool = False,
                write_data: int = 0, write_mask: int = 0xFF,
                response_data: int = 0):
        line = addr & ~0x3F
        own, other = self.states[line][core], self.states[line][1 - core]
        old_states = tuple(self.states[line])
        if ((write and other == "M") or
                (not write and own == "I" and other in ("M", "E"))):
            # OwnerData from an M or E holder is accepted by the L2 line port
            # before Grant; that full-line write advances the L2 replacement
            # pointer even when the architectural value is still clean.
            self._touch_l2_write(line)
        expected, event = self.predict(core, addr, write=write,
                                       write_data=write_data,
                                       write_mask=write_mask)
        if not write and response_data != expected:
            raise AssertionError(
                f"core{core} read {addr:#x}: got {response_data:#018x}, "
                f"expected {expected:#018x} ({event})"
            )

        l2_refill = None
        if own == "I":
            # A blocking L1 completes its local victim Put before the miss is
            # admitted to the shared L2. That writeback can advance the L2
            # replacement pointer, so model the L1 victim first.
            self._allocate_l1(core, line)
            l2_was_present = self._ensure_l2_line(line)
            l2_refill = "hit" if l2_was_present else "miss"

        if own != "I":
            data_source = "l1"
        elif other in ("M", "E"):
            data_source = "remote_owner"
        elif other == "S" or l2_refill == "hit":
            data_source = "shared_l2"
        else:
            data_source = "memory"
        snoop_target = 1 - core if other != "I" else None
        line_transfer_beats = 8 if own == "I" else 0

        if write:
            self.states[line][core] = "M"
            self.states[line][1 - core] = "I"
            self._remove_l1_copy(1 - core, line)
            key = addr & ~0x7
            self.data[key] = self._merge_bytes(self.data.get(key, 0),
                                               write_data, write_mask)
        elif own == "I":
            if other == "I":
                self.states[line][core] = "E"
            else:
                self.states[line][core] = "S"
                if other in ("E", "M"):
                    self.states[line][1 - core] = "S"

        self.events.add(event)
        self.event_counts[event] += 1
        if l2_refill is not None:
            self.event_counts[f"l2_refill_{l2_refill}"] += 1
        self.directory[line] = self.directory_view(line)
        self.transitions.append({
            "line": line, "core": core, "op": "write" if write else "read",
            "old_state": old_states, "new_state": tuple(self.states[line]),
            "event": event, "write_mask": write_mask if write else 0,
            "l2_refill": l2_refill,
            "data_source": data_source, "snoop_target": snoop_target,
            "line_transfer_beats": line_transfer_beats,
        })
        self._assert_line_invariants(line)
        return expected, event

    def assert_covered(self, *required_events):
        missing = sorted(set(required_events) - self.events)
        if missing:
            raise AssertionError(f"coherence functional bins not hit: {missing}")
