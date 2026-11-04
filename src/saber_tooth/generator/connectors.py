"""Arcs and chains (v3 `sliders` and `burstSliders`) laid over notes the placer has kept.

Arcs join two single hits of one hand in a calm passage when the second swing flows out of the
first. Chains extend an accented single hit in a high-energy phrase along its own cut. A connector
never touches another note, a wall, a bomb or another connector, and never changes a note, so the
swing direction and parity the placer verified stay as they were."""

import bisect
import math
from dataclasses import dataclass
from itertools import pairwise

from saber_tooth.model import CUT_VECTORS, Color, Cut, Difficulty, Note
from saber_tooth.profiles import Profile
from saber_tooth.swings import Swing, angle_between, build_swings
from saber_tooth.timing import Timing

BAR = 4.0
GRID_W, GRID_H = 4, 3
CALM, BUSY = 0.45, 0.7  # normalised note density per bar
ARC_MIN_BEATS, ARC_MAX_BEATS = 1.0, 4.0
ARC_MIN_TURN = 135.0  # degrees between the two cut vectors: a clean there-and-back swing
CHAIN_BEATS = 0.5
CHAIN_ROOM = 0.5  # beats of free time kept between the chain tail and the hand's next swing
MARGIN = 0.25  # beats kept clear of walls and bombs
EPS = 0.05  # beats: notes this close to a connector's span count as inside it
ACCENT_S = 0.06
# Share of eligible spots that take a connector, per difficulty; Easy has none.
ARC_SHARE = {"Normal": 0.2, "Hard": 0.3, "Expert": 0.4, "ExpertPlus": 0.5}
CHAIN_SHARE = {"Hard": 0.15, "Expert": 0.25, "ExpertPlus": 0.35}


@dataclass(frozen=True)
class _Span:
    lo: float
    hi: float
    x0: int
    x1: int
    y0: int
    y1: int

    def inside(self, n: Note) -> bool:
        return self.x0 <= n.x <= self.x1 and self.y0 <= n.y <= self.y1

    def meets(self, o: "_Span") -> bool:
        return (
            self.lo - EPS <= o.hi
            and o.lo - EPS <= self.hi
            and self.x0 <= o.x1
            and o.x0 <= self.x1
            and self.y0 <= o.y1
            and o.y0 <= self.y1
        )


def bar_energy(notes: list[Note]) -> list[float]:
    """Note count per 4-beat bar, divided by the 90th percentile and capped at 1."""
    if not notes:
        return []
    counts = [0] * (max(0, int(max(n.beat for n in notes) // BAR)) + 1)
    for n in notes:
        counts[max(0, int(n.beat // BAR))] += 1
    ranked = sorted(counts)
    top = ranked[min(len(ranked) - 1, math.ceil(0.9 * len(ranked)) - 1)] or ranked[-1]
    return [min(1.0, c / top) for c in counts]


def _energy_at(energy: list[float], beat: float) -> float:
    return energy[min(len(energy) - 1, max(0, int(beat // BAR)))] if energy else 0.0


def _singles(swings: list[Swing]) -> list[tuple[int, Swing]]:
    return [(i, s) for i, s in enumerate(swings) if len(s.notes) == 1 and s.notes[0].cut != Cut.ANY]


class _Field:
    """What a new connector must keep clear of."""

    def __init__(self, d: Difficulty):
        self.notes = sorted(d.notes)
        self.beats = [n.beat for n in self.notes]
        self.d = d
        self.spans: list[_Span] = []
        self.used: set[Note] = set()

    def clear(self, span: _Span, own: tuple[Note, ...]) -> bool:
        if any(n in self.used for n in own):
            return False
        if any(w.beat < span.hi + MARGIN and w.beat + w.duration > span.lo - MARGIN
               for w in self.d.walls):  # fmt: skip
            return False
        if any(span.lo - MARGIN <= b.beat <= span.hi + MARGIN for b in self.d.bombs):
            return False
        i = bisect.bisect_left(self.beats, span.lo - EPS)
        j = bisect.bisect_right(self.beats, span.hi + EPS)
        if any(n not in own and span.inside(n) for n in self.notes[i:j]):
            return False
        return not any(span.meets(o) for o in self.spans)

    def take(self, span: _Span, own: tuple[Note, ...]) -> None:
        self.spans.append(span)
        self.used.update(own)


def _arc_json(a: Note, b: Note) -> dict:
    return {
        "b": a.beat, "c": int(a.color), "x": a.x, "y": a.y, "d": int(a.cut), "mu": 1.0,
        "tb": b.beat, "tx": b.x, "ty": b.y, "tc": int(b.cut), "tmu": 1.0, "m": 0,
    }  # fmt: skip


def _chain_json(n: Note, tail: tuple[int, int], tb: float, links: int) -> dict:
    return {
        "b": n.beat, "c": int(n.color), "x": n.x, "y": n.y, "d": int(n.cut),
        "tb": tb, "tx": tail[0], "ty": tail[1], "sc": links, "s": 1.0,
    }  # fmt: skip


def _flows(first: Note, second: Note) -> bool:
    """The second hit is a clean reversal of the first and lies ahead along its swing."""
    u, v = CUT_VECTORS[first.cut], CUT_VECTORS[second.cut]
    if angle_between(u, v) < ARC_MIN_TURN:
        return False
    dx, dy = second.x - first.x, second.y - first.y
    return (dx, dy) != (0, 0) and dx * u[0] + dy * u[1] >= 0


def _arcs(d: Difficulty, swings: dict[Color, list[Swing]], energy, field: _Field, share) -> list:
    out: list[dict] = []
    every = max(1, round(1 / share))
    pairs = []
    for hand_swings in swings.values():
        singles = _singles(hand_swings)
        for (i, s1), (j, s2) in pairwise(singles):
            a, b = s1.notes[0], s2.notes[0]
            gap = b.beat - a.beat
            calm = max(_energy_at(energy, a.beat), _energy_at(energy, b.beat)) <= CALM
            if j == i + 1 and ARC_MIN_BEATS <= gap <= ARC_MAX_BEATS and calm and _flows(a, b):
                pairs.append((a, b))
    since = every  # the first eligible spot takes one
    for a, b in sorted(pairs, key=lambda p: (p[0].beat, p[0].color)):
        since += 1
        span = _Span(
            a.beat,
            b.beat,
            max(0, min(a.x, b.x) - 1),
            min(GRID_W - 1, max(a.x, b.x) + 1),
            max(0, min(a.y, b.y) - 1),
            min(GRID_H - 1, max(a.y, b.y) + 1),
        )
        if since >= every and field.clear(span, (a, b)):
            field.take(span, (a, b))
            out.append(_arc_json(a, b))
            since = 0
    return out


def _accented(s: Swing, accents: list[float] | None) -> bool:
    if accents is None:
        return s.notes[0].beat % 2 == 0  # no audio: the downbeats of each bar pair
    k = bisect.bisect_left(accents, s.seconds - ACCENT_S)
    return k < len(accents) and accents[k] <= s.seconds + ACCENT_S


def _tail(n: Note) -> tuple[tuple[int, int], int] | None:
    """Tail cell and link count: two cells along the cut when the grid allows, else one."""
    v = CUT_VECTORS[n.cut]
    dx, dy = round(v[0]), round(v[1])
    for length in (2, 1):
        x, y = n.x + dx * length, n.y + dy * length
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            return (x, y), length + 2
    return None


def _chains(swings, energy, field: _Field, share, accents) -> list[dict]:
    out: list[dict] = []
    every = max(1, round(1 / share))
    spots = []
    for hand_swings in swings.values():
        for i, s in _singles(hand_swings):
            n = s.notes[0]
            nxt = hand_swings[i + 1].notes[0].beat if i + 1 < len(hand_swings) else math.inf
            if (
                _energy_at(energy, n.beat) >= BUSY
                and nxt - n.beat >= CHAIN_BEATS + CHAIN_ROOM
                and _accented(s, accents)
                and _tail(n)
            ):
                spots.append(n)
    since = every  # the first eligible spot takes one
    for n in sorted(spots, key=lambda n: (n.beat, n.color)):
        since += 1
        tail, links = _tail(n)  # type: ignore[misc]  # filtered above
        span = _Span(
            n.beat, n.beat + CHAIN_BEATS, min(n.x, tail[0]), max(n.x, tail[0]),
            min(n.y, tail[1]), max(n.y, tail[1]),
        )  # fmt: skip
        if since >= every and field.clear(span, (n,)):
            field.take(span, (n,))
            out.append(_chain_json(n, tail, n.beat + CHAIN_BEATS, links))
            since = 0
    return out


def add_connectors(
    d: Difficulty, timing: Timing, profile: Profile, accents: list[float] | None = None
) -> tuple[int, int]:
    """Put arcs and chains into `d.raw`; the (arcs, chains) counts. `accents` are the seconds of
    the strong drum hits, sorted; without them chains go on the downbeats."""
    arc_share = ARC_SHARE.get(profile.name, 0.0)
    chain_share = CHAIN_SHARE.get(profile.name, 0.0)
    if (not arc_share and not chain_share) or not d.notes:
        return 0, 0
    swings = build_swings(d.notes, timing)
    energy = bar_energy(d.notes)
    field = _Field(d)
    chains = _chains(swings, energy, field, chain_share, accents) if chain_share else []
    arcs = _arcs(d, swings, energy, field, arc_share) if arc_share else []
    d.raw["sliders"] = sorted([*d.raw.get("sliders", []), *arcs], key=lambda s: s["b"])
    d.raw["burstSliders"] = sorted([*d.raw.get("burstSliders", []), *chains], key=lambda s: s["b"])
    return len(arcs), len(chains)
