"""CPU-visible memory semantics and an independent cache-tag state model."""

from dataclasses import dataclass

from dv.common.transaction import SimpleBusRequest, SimpleBusResponse
from dv.common.utils.cmd_code import (
    CMD_READ,
    CMD_READLST,
    CMD_WRITE,
    CMD_WRITERSP,
)


@dataclass(frozen=True, order=True)
class _LineState:
    """One possible resident line in the architectural cache-state model."""

    tag: int
    dirty: bool


@dataclass(frozen=True)
class CacheAccessPrediction:
    """Architectural hit/miss prediction plus legal dirty-victim choices."""

    outcome: str
    dirty_victims: frozenset[int]
    dirty_victim_required: bool


class LfsrReplacementModel:
    """Independent cycle-by-cycle predictor for CacheStage2's victim LFSR."""

    SEED = 0x1234567887654321
    MASK64 = (1 << 64) - 1

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = self.SEED

    def tick(self, reset=False):
        """Advance once per RTL clock, or reload the RTL reset seed."""
        if reset:
            self.reset()
        elif self.state == 0:
            self.state = 1
        else:
            feedback = (
                (self.state >> 0) ^ (self.state >> 1)
                ^ (self.state >> 3) ^ (self.state >> 4)
            ) & 1
            self.state = ((feedback << 63) | (self.state >> 1)) & self.MASK64
        return self.mask

    @property
    def mask(self):
        return 1 << (self.state & 0x3)


class SetAssociativeTagModel:
    """Four-way tag/valid/dirty model with nondeterministic full-set victims.

    The RTL prefers the highest-numbered invalid way, then uses an LFSR victim
    when a set is full.  Since the LFSR is intentionally pseudo-random, this
    model tracks every architecturally legal replacement outcome rather than
    copying the implementation's internal state.  Observed backing-memory
    traffic resolves each access as hit or miss and prunes the candidate
    states; impossible hit/miss sequences fail immediately.
    """

    SETS = 128
    WAYS = 4
    LINE_BYTES = 64
    MAX_CANDIDATE_STATES_PER_SET = 4096

    def __init__(self):
        self.replacement = LfsrReplacementModel()
        self.reset()

    def reset(self):
        self._states = {}
        self.replacement.reset()
        self.hits = 0
        self.misses = 0
        self.ambiguous_outcomes = 0

    @staticmethod
    def address_fields(addr):
        addr &= 0xFFFFFFFF
        return (addr >> 6) & 0x7F, addr >> 13

    @staticmethod
    def invalid_first_way(valid_mask):
        """Return the RTL's highest-numbered invalid way, or None if full."""
        invalid = (~valid_mask) & 0xF
        for way in range(3, -1, -1):
            if invalid & (1 << way):
                return way
        return None

    @staticmethod
    def line_base(set_index, tag):
        return ((tag << 7) | set_index) << 6

    def predict_access(self, request, was_miss=None):
        """Predict hit/miss from model state without consulting bus traffic.

        was_miss is only supplied after an observed access when several
        abstract states make both outcomes legal. It narrows the victim set
        for writeback checking; it does not override a deterministic
        prediction.
        """
        if request.cmd not in (CMD_READ, CMD_WRITE):
            raise ValueError(f"unsupported tag-model command 0x{request.cmd:x}")
        set_index, tag = self.address_fields(request.addr)
        states = self._states.get(set_index, {()})
        hit_states = [state for state in states if any(line.tag == tag for line in state)]
        miss_states = [state for state in states if not any(line.tag == tag for line in state)]
        if not hit_states:
            outcome = "miss"
        elif not miss_states:
            outcome = "hit"
        else:
            outcome = "ambiguous"

        if was_miss is True:
            considered = miss_states
        elif was_miss is False:
            considered = hit_states
        else:
            considered = list(states)
        if not considered:
            observed = "miss" if was_miss else "hit"
            raise AssertionError(
                f"tag model: observed {observed} for impossible tag 0x{tag:x} "
                f"in set {set_index}"
            )

        victim_options = []
        dirty_victims = set()
        for state in considered:
            if any(line.tag == tag for line in state):
                victim_options.append(None)
            elif len(state) < self.WAYS:
                victim_options.append(None)
            else:
                for line in state:
                    if line.dirty:
                        victim_address = self.line_base(set_index, line.tag)
                        dirty_victims.add(victim_address)
                        victim_options.append(victim_address)
                    else:
                        victim_options.append(None)

        dirty_victim_required = bool(victim_options) and all(
            option is not None for option in victim_options
        )
        return CacheAccessPrediction(
            outcome=outcome,
            dirty_victims=frozenset(dirty_victims),
            dirty_victim_required=dirty_victim_required,
        )

    def observe_access(self, request, was_miss):
        """Commit one completed CPU access using observed refill presence.

        Each candidate is an immutable tuple of resident ``(tag, dirty)``
        entries. The abstraction intentionally ignores physical way identity;
        it still enforces four-way capacity, hit/miss consistency, and dirty
        state across all legal LFSR victim choices.
        """
        if request.cmd not in (CMD_READ, CMD_WRITE):
            return
        prediction = self.predict_access(request)
        if prediction.outcome == "hit" and was_miss:
            raise AssertionError(
                f"tag model: observed backing-memory miss for predicted hit at "
                f"0x{request.addr:08x}"
            )
        if prediction.outcome == "miss" and not was_miss:
            raise AssertionError(
                f"tag model: observed hit for predicted miss at 0x{request.addr:08x}"
            )
        set_index, tag = self.address_fields(request.addr)
        states = self._states.get(set_index, {()})
        matches = [state for state in states if any(line.tag == tag for line in state)]

        if was_miss:
            candidates = [state for state in states if not any(line.tag == tag for line in state)]
            if not candidates:
                raise AssertionError(
                    f"tag model: reported miss for resident tag 0x{tag:x} in set {set_index}"
                )
            next_states = set()
            new_line = _LineState(tag, request.cmd == CMD_WRITE)
            for state in candidates:
                if len(state) < self.WAYS:
                    next_states.add(tuple(sorted((*state, new_line))))
                else:
                    for victim_index in range(self.WAYS):
                        next_states.add(
                            tuple(sorted((*state[:victim_index], *state[victim_index + 1:], new_line)))
                        )
            self.misses += 1
            if len(next_states) > 1:
                self.ambiguous_outcomes += 1
        else:
            if not matches:
                raise AssertionError(
                    f"tag model: reported hit for absent tag 0x{tag:x} in set {set_index}"
                )
            next_states = set()
            for state in matches:
                updated = tuple(
                    sorted(
                        _LineState(line.tag, line.dirty or request.cmd == CMD_WRITE)
                        if line.tag == tag else line
                        for line in state
                    )
                )
                next_states.add(updated)
            self.hits += 1

        if len(next_states) > self.MAX_CANDIDATE_STATES_PER_SET:
            raise AssertionError(
                f"tag model: candidate-state limit exceeded in set {set_index}; "
                "split the stress into reset-bounded scenarios or add a sound abstraction"
            )
        self._states[set_index] = next_states

    def candidate_states(self, set_index):
        """Read-only state view for unit tests and debug reports."""
        return frozenset(self._states.get(set_index, {()}))

    def occupancy(self, addr):
        """Return the pre-access resident-line count, or None if ambiguous."""
        set_index, _tag = self.address_fields(addr)
        counts = {len(state) for state in self._states.get(set_index, {()})}
        return next(iter(counts)) if len(counts) == 1 else None

    def observe_probe(self, addr, was_hit):
        """Check an observed probe result and invalidate the line on a hit."""
        set_index, tag = self.address_fields(addr)
        states = self._states.get(set_index, {()})
        if was_hit:
            candidates = [state for state in states if any(line.tag == tag for line in state)]
            if not candidates:
                raise AssertionError(
                    f"tag model: reported probe hit for absent tag 0x{tag:x} in set {set_index}"
                )
            next_states = {
                tuple(line for line in state if line.tag != tag)
                for state in candidates
            }
        else:
            candidates = [state for state in states if not any(line.tag == tag for line in state)]
            if not candidates:
                raise AssertionError(
                    f"tag model: reported probe miss for resident tag 0x{tag:x} in set {set_index}"
                )
            next_states = set(candidates)
        self._states[set_index] = next_states


class CacheReferenceModel:
    """Sparse 64-bit memory model with SimpleBus byte-enable semantics."""

    WORD_MASK = (1 << 64) - 1

    def __init__(self):
        self.data = {}
        self.cache_tags = SetAssociativeTagModel()

    @staticmethod
    def is_mmio(addr):
        # Mirrors CacheStage2's current decode: 0x3xxx_xxxx and 0x4xxx_xxxx-
        # 0x7xxx_xxxx are bypassed to the MMIO port.
        return 0x30000000 <= addr < 0x40000000 or 0x40000000 <= addr < 0x80000000

    def predict(self, request):
        if not isinstance(request, SimpleBusRequest):
            request = SimpleBusRequest(**request)
        addr = request.addr & ~0x7
        old = self.data.get(addr, 0)
        if request.cmd == CMD_READ:
            return SimpleBusResponse(CMD_READLST, old)
        if request.cmd == CMD_WRITE:
            byte_mask = sum(
                0xFF << (8 * lane)
                for lane in range(8)
                if request.wmask & (1 << lane)
            )
            self.data[addr] = ((old & ~byte_mask) | (request.wdata & byte_mask)) & self.WORD_MASK
            return SimpleBusResponse(CMD_WRITERSP, old)
        raise ValueError(f"unsupported CPU command 0x{request.cmd:x} at 0x{request.addr:08x}")

    def observe_cache_access(self, request, was_miss):
        """Update tag/valid/dirty state after the response has retired."""
        if not self.is_mmio(request.addr):
            self.cache_tags.observe_access(request, was_miss)

    def reset_cache_state(self):
        """Model the tag-array invalidation performed by DUT reset."""
        self.cache_tags.reset()

    def probe_release_data(self, addr):
        """Expected 8-beat line release, beginning at the probed word."""
        line_base = addr & ~0x3F
        first_word = (addr >> 3) & 0x7
        return [
            self.data.get(line_base | (((first_word + beat) & 0x7) << 3), 0)
            for beat in range(8)
        ]

    def observe_probe(self, addr, was_hit):
        if not self.is_mmio(addr):
            self.cache_tags.observe_probe(addr, was_hit)
