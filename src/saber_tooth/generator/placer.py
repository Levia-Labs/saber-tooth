import math
from bisect import bisect_left, bisect_right, insort
from collections.abc import Iterable
from dataclasses import dataclass

from saber_tooth.checks.constants import PARITY_DOT, VISION_MIN_DT, cells_per_second
from saber_tooth.checks.layout import SAME_CELL_S, converges, jump_window_s
from saber_tooth.generator.motifs import Step, lattice, pool
from saber_tooth.model import CUT_VECTORS, Color, Cut, Note
from saber_tooth.profiles import Profile
from saber_tooth.swings import DEFAULT_PREV, Vec
from saber_tooth.timing import Timing

GAP_MARGIN_S = 1e-3
SPEED_MARGIN = 0.98
MAX_PARITY_DOT = min(PARITY_DOT, -0.5)  # stricter than the check: clearly alternating swings
VISION_MARGIN_S = 1e-3
PIN_DOT = 0.5  # a dot must stay within 60 degrees of the vector it had before the fill


class GenerationError(Exception):
    """The placer produced a map the checks reject; always a bug."""


@dataclass(frozen=True)
class Link:
    secs: float
    vec: tuple[float, float] | None  # None for a dot note: no direction, so no parity limit
    pos: tuple[int, int]


def _link(note: Note, secs: float) -> Link:
    return Link(secs, CUT_VECTORS.get(note.cut), (note.x, note.y))


def _parity_clash(a: tuple[float, float] | None, b: tuple[float, float] | None) -> bool:
    """Two swings that point the same way in a row; a dot has no direction and never clashes."""
    if a is None or b is None:
        return False
    return a[0] * b[0] + a[1] * b[1] > MAX_PARITY_DOT


def is_vision_spot(x: int, y: int) -> bool:
    return x in (1, 2) and y == 1


class Placer:
    """Verifies each candidate step against the limits the checks use before keeping it."""

    def __init__(
        self,
        timing: Timing,
        profile: Profile,
        context: Iterable[Note] = (),
        pinned: dict[Note, Vec] | None = None,
    ):
        self.timing, self.profile = timing, profile
        # swing vector each context dot had in the map before the fill: the fill must keep it
        self.pinned: dict[Note, Vec] = pinned or {}
        self.secs: dict[Color, list[float]] = {Color.RED: [], Color.BLUE: []}
        self.notes: dict[Color, list[Note]] = {Color.RED: [], Color.BLUE: []}
        self.all_secs: list[float] = []
        self.vision: list[float] = []
        self.cells: list[tuple[float, int, int]] = []  # every note by time, for flight paths
        self.window = jump_window_s(profile.njs, profile.offset, timing.initial_bpm)
        self.context: set[Note] = set()
        self._pools = {h: pool(h) for h in Color}
        self._lattice = {h: lattice(h) for h in Color}
        for n in sorted(context):
            self.add(n, context=True)

    @classmethod
    def from_notes(
        cls, timing, profile, notes: Iterable[Note], context=(), pinned=None
    ) -> "Placer":
        placer = cls(timing, profile, context, pinned)
        for n in sorted(notes):
            placer.add(n)
        return placer

    def all_notes(self, with_context: bool = False) -> list[Note]:
        notes = self.notes[Color.RED] + self.notes[Color.BLUE]
        return sorted(n for n in notes if with_context or n not in self.context)

    def add(self, note: Note, context: bool = False) -> None:
        if context:
            self.context.add(note)
        s = self.timing.to_seconds(note.beat)
        i = bisect_left(self.secs[note.color], s)
        self.secs[note.color].insert(i, s)
        self.notes[note.color].insert(i, note)
        insort(self.all_secs, s)
        insort(self.cells, (s, note.x, note.y))
        if is_vision_spot(note.x, note.y):
            insort(self.vision, s)

    def last_secs(self, hand: Color, before: float = math.inf) -> float:
        i = bisect_left(self.secs[hand], before)
        return self.secs[hand][i - 1] if i else -math.inf

    def _effective(self, hand: Color, i: int) -> Vec | None:
        """Swing vector of the hand's i-th note; a dot goes opposite to the swing before it."""
        notes, flips = self.notes[hand], 0
        while i >= 0 and notes[i].cut == Cut.ANY and notes[i] not in self.pinned:
            i, flips = i - 1, flips + 1
        base = DEFAULT_PREV if i < 0 else self.pinned.get(notes[i]) or CUT_VECTORS[notes[i].cut]
        sign = -1 if flips % 2 else 1
        return (sign * base[0], sign * base[1])

    def _neighbours(self, hand: Color, s: float) -> tuple[Link | None, Link | None]:
        i = bisect_left(self.secs[hand], s)
        prev = nxt = None
        if i:
            prev = Link(
                self.secs[hand][i - 1], self._effective(hand, i - 1), self._pos(hand, i - 1)
            )
        if i < len(self.secs[hand]):
            nxt = _link(self.notes[hand][i], self.secs[hand][i])
        return prev, nxt

    def _pos(self, hand: Color, i: int) -> tuple[int, int]:
        return self.notes[hand][i].x, self.notes[hand][i].y

    def _dot_run_clash(self, hand: Color, s: float, me: Link) -> bool:
        """A dot after `me` flips with it; the swing behind the dots must still alternate."""
        i = bisect_left(self.secs[hand], s)
        notes, flips = self.notes[hand], 0
        if i < len(notes) and me.vec is not None and notes[i] in self.pinned:
            pin = self.pinned[notes[i]]  # the dot must keep the vector the swing after it expects
            return -(me.vec[0] * pin[0] + me.vec[1] * pin[1]) < PIN_DOT
        while i < len(notes) and notes[i].cut == Cut.ANY:
            i, flips = i + 1, flips + 1
        if not flips or i >= len(notes) or me.vec is None:
            return False
        sign = -1 if flips % 2 else 1
        return _parity_clash((sign * me.vec[0], sign * me.vec[1]), CUT_VECTORS[notes[i].cut])

    def _linked(self, a: Link, b: Link, relaxed: bool = False) -> bool:
        warn = self.profile.warn
        dt = b.secs - a.secs
        if dt < warn.min_hand_gap_s + GAP_MARGIN_S:
            return False
        # after a long pause the swing direction is free; only used when no alternating step fits
        free = relaxed and dt >= warn.reset_window_s + GAP_MARGIN_S
        if not free and _parity_clash(a.vec, b.vec):
            return False
        return cells_per_second(a.pos, b.pos, dt) <= warn.max_hand_speed * SPEED_MARGIN

    def _vision_ok(self, s: float, step: Step, next_s: float | None) -> bool:
        window = self.profile.warn.vision_window_s + VISION_MARGIN_S
        i = bisect_left(self.vision, s - window)
        if i < len(self.vision) and self.vision[i] < s - VISION_MIN_DT:
            return False  # an earlier centre note would now block this one
        if not is_vision_spot(step[1], step[2]):
            return True
        if self.profile.name != "ExpertPlus":
            return False
        j = bisect_right(self.all_secs, s + VISION_MIN_DT)
        if j < len(self.all_secs) and self.all_secs[j] <= s + window:
            return False
        return next_s is None or next_s - s > window or next_s - s <= VISION_MIN_DT

    def _converges(self, s: float, step: Step) -> bool:
        """A note near in time would fly into this one's spot while jumping to its row."""
        reach = max(self.window, SAME_CELL_S) + GAP_MARGIN_S
        i = bisect_left(self.cells, (s - reach,))
        while i < len(self.cells) and self.cells[i][0] <= s + reach:
            t, x, y = self.cells[i]
            if converges(t - s, (x, y), (step[1], step[2]), self.window):
                return True
            i += 1
        return False

    def _fits(self, hand: Color, s, step: Step, prev, nxt, next_s, relaxed: bool) -> bool:
        if self._converges(s, step):
            return False
        me = Link(s, CUT_VECTORS[step[0]], (step[1], step[2]))
        if prev is not None and not self._linked(prev, me, relaxed):
            return False
        if nxt is not None and not self._linked(me, nxt, relaxed):
            return False
        if nxt is not None and self._dot_run_clash(hand, s, me):
            return False
        return self._vision_ok(s, step, next_s)

    def _ordered(self, hand: Color, preferred: list[Step], prev: Link | None) -> Iterable[Step]:
        yield from preferred
        origin = prev.pos if prev else (1 if hand == Color.RED else 2, 0)
        for source in (self._pools[hand], self._lattice[hand]):
            yield from sorted(source, key=lambda st: math.dist(origin, (st[1], st[2])))

    def try_add(
        self, hand: Color, beat: float, preferred: list[Step], next_s: float | None = None
    ) -> Step | None:
        """Place one note for `hand`; returns the chosen step, or None when nothing fits."""
        s = self.timing.to_seconds(beat)
        prev, nxt = self._neighbours(hand, s)
        for relaxed in (False, True):
            for step in self._ordered(hand, preferred, prev):
                if self._fits(hand, s, step, prev, nxt, next_s, relaxed):
                    cut, x, y = step
                    self.add(Note(beat, x, y, hand, cut))
                    return step
        return None
