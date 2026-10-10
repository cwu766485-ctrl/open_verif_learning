"""CPU-visible memory semantics and an independent cache-tag state model."""

from collections import defaultdict, deque
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
    """A resident tag, with its exact physical way in the set."""

    tag: int
    dirty: bool
    way: int


@dataclass(frozen=True)
class CacheAccessPrediction:
    """Exact hit/miss and victim prediction for one cache access."""

    outcome: str
    dirty_victims: frozenset[int]
    dirty_victim_required: bool
    selected_way: int | None = None
    occupancy_before: int = 0


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
    """Four-way tag/valid/dirty model with exact physical-way replacement.

    At the Stage2-to-Stage3 transfer, the model independently predicts the
    hit/miss result and selected refill way, compares them against the
    observed RTL event and LFSR sample, then updates its way-indexed state.
    It retains the pre-update prediction until the CPU response retires so the
    scoreboard can check the exact dirty victim and writeback payload.
    """

    SETS = 128
    WAYS = 4
    LINE_BYTES = 64
    def __init__(self):
        self.replacement = LfsrReplacementModel()
        self.reset()

    def reset(self):
        self._states = {}
        self._access_history = defaultdict(deque)
        self.replacement.reset()
        self.hits = 0
        self.misses = 0
        self.exact_way_updates = 0

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

    @staticmethod
    def _ordered(state):
        return tuple(sorted(state, key=lambda line: line.way))

    @staticmethod
    def _valid_mask(state):
        return sum(1 << line.way for line in state)

    @staticmethod
    def _is_onehot_way(mask):
        return 0 < mask <= 0xF and (mask & (mask - 1)) == 0

    def _next_refill_way(self, state, lfsr_way_mask=None):
        invalid_way = self.invalid_first_way(self._valid_mask(state))
        if invalid_way is not None:
            return invalid_way
        mask = self.replacement.mask if lfsr_way_mask is None else lfsr_way_mask
        if not self._is_onehot_way(mask):
            raise AssertionError(f"tag model: invalid LFSR way mask 0x{mask:x}")
        return mask.bit_length() - 1

    def predict_access(
        self, request, was_miss=None, *, selected_way_mask=None, lfsr_way_mask=None
    ):
        """Predict hit/miss and the exact way selected for a refill."""
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
            raise AssertionError(
                f"tag model: physical-way state is ambiguous for tag 0x{tag:x} "
                f"in set {set_index}; exact replacement history was lost"
            )

        if was_miss is not None and (outcome == "miss") != bool(was_miss):
            observed = "miss" if was_miss else "hit"
            raise AssertionError(
                f"tag model: observed {observed} for predicted {outcome} at "
                f"0x{request.addr:08x} in set {set_index}"
            )

        state = next(iter(hit_states or miss_states))
        hit_line = next((line for line in state if line.tag == tag), None)
        selected_way = hit_line.way if hit_line is not None else self._next_refill_way(
            state, lfsr_way_mask
        )
        expected_mask = 1 << selected_way
        if selected_way_mask is not None and selected_way_mask != expected_mask:
            raise AssertionError(
                f"tag model: RTL selected way mask 0x{selected_way_mask:x}, expected "
                f"0x{expected_mask:x} for {'hit' if hit_line else 'refill'} "
                f"at 0x{request.addr:08x}"
            )

        victim = next((line for line in state if line.way == selected_way), None)
        dirty_victims = frozenset((self.line_base(set_index, victim.tag),)) if (
            outcome == "miss" and victim is not None and victim.dirty
        ) else frozenset()
        return CacheAccessPrediction(
            outcome=outcome,
            dirty_victims=dirty_victims,
            dirty_victim_required=bool(dirty_victims),
            selected_way=selected_way,
            occupancy_before=len(state),
        )

    def observe_access(
        self, request, was_miss, *, selected_way_mask=None, lfsr_way_mask=None,
        record_prediction=True,
    ):
        """Cross-check one Stage2 event and update exact physical-way state.

        The saved prediction describes the pre-access state. The scoreboard
        consumes it only when that CPU request's response retires.
        """
        if request.cmd not in (CMD_READ, CMD_WRITE):
            return None
        prediction = self.predict_access(
            request,
            was_miss,
            selected_way_mask=selected_way_mask,
            lfsr_way_mask=lfsr_way_mask,
        )
        set_index, tag = self.address_fields(request.addr)
        state = next(iter(self._states.get(set_index, {()})))
        if was_miss:
            way = prediction.selected_way
            survivors = [line for line in state if line.way != way]
            survivors.append(_LineState(tag, request.cmd == CMD_WRITE, way))
            self._states[set_index] = {self._ordered(survivors)}
            self.misses += 1
        else:
            self._states[set_index] = {
                self._ordered(
                    _LineState(line.tag, line.dirty or request.cmd == CMD_WRITE, line.way)
                    if line.tag == tag else line
                    for line in state
                )
            }
            self.hits += 1
        self.exact_way_updates += 1
        if record_prediction:
            key = (request.addr & ~0x3F, request.cmd)
            self._access_history[key].append((prediction, bool(was_miss)))
        return prediction

    def consume_access_prediction(self, request):
        """Consume the saved pre-update oracle for a retired CPU request."""
        key = (request.addr & ~0x3F, request.cmd)
        history = self._access_history.get(key)
        if not history:
            return None
        prediction, _was_miss = history.popleft()
        if not history:
            self._access_history.pop(key, None)
        return prediction

    def candidate_states(self, set_index):
        """Compatibility view; each set now has one exact physical-way state."""
        return frozenset(self._states.get(set_index, {()}))

    def occupancy(self, addr):
        """Return exact set occupancy."""
        set_index, _tag = self.address_fields(addr)
        counts = {len(state) for state in self._states.get(set_index, {()})}
        return next(iter(counts))

    def observe_probe(self, addr, was_hit):
        """Check an observed probe result and invalidate the line on a hit."""
        set_index, tag = self.address_fields(addr)
        states = self._states.get(set_index, {()})
        if len(states) != 1:
            raise AssertionError(f"tag model: expected exact state for probe in set {set_index}")
        state = next(iter(states))
        resident = any(line.tag == tag for line in state)
        if resident != bool(was_hit):
            observed = "hit" if was_hit else "miss"
            raise AssertionError(
                f"tag model: reported probe {observed} for "
                f"{'resident' if resident else 'absent'} tag 0x{tag:x} in set {set_index}"
            )
        if was_hit:
            self._states[set_index] = {
                tuple(line for line in state if line.tag != tag)
            }


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

    def observe_cache_access(self, request, was_miss, *, record_prediction=True):
        """Update tag/valid/dirty state after the response has retired."""
        if not self.is_mmio(request.addr):
            self.cache_tags.observe_access(
                request, was_miss, record_prediction=record_prediction
            )

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
