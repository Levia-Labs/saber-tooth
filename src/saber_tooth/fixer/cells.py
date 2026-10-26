"""Grid and swing helpers shared by the fix strategies."""

import math

from saber_tooth.fixer.verify import Context
from saber_tooth.model import CUT_VECTORS, Color, Cut, Note
from saber_tooth.swings import Swing, build_swings

EPS = 1e-6
CELLS = [(x, y) for x in range(4) for y in range(3)]
RING = [
    Cut.UP,
    Cut.UP_RIGHT,
    Cut.RIGHT,
    Cut.DOWN_RIGHT,
    Cut.DOWN,
    Cut.DOWN_LEFT,
    Cut.LEFT,
    Cut.UP_LEFT,
]


def nearest_cut(vec: tuple[float, float]) -> Cut:
    return max(CUT_VECTORS, key=lambda c: CUT_VECTORS[c][0] * vec[0] + CUT_VECTORS[c][1] * vec[1])


def step_of(cut: Cut) -> tuple[int, int]:
    """Whole-cell step along a cut direction."""
    vx, vy = CUT_VECTORS[cut]
    return round(vx), round(vy)


def occupied(ctx: Context, beat: float, skip: tuple[Note, ...] = ()) -> set[tuple[int, int]]:
    return {(n.x, n.y) for n in ctx.d.notes if abs(n.beat - beat) < EPS and n not in skip}


def by_distance(origin: tuple[int, int]) -> list[tuple[int, int]]:
    return sorted(CELLS, key=lambda c: (math.dist(c, origin), c))


def swing_pair(ctx: Context) -> tuple[Swing, Swing] | None:
    """The consecutive same-hand swings a flow finding refers to."""
    f = ctx.finding
    swings = build_swings(ctx.d.notes, ctx.timing)
    for hand in Color:
        for a, b in zip(swings[hand], swings[hand][1:], strict=False):
            at = abs(a.beat - f.beat_start) < EPS and abs(b.beat - f.beat_end) < EPS
            if at and set(a.notes + b.notes) == set(f.notes):
                return a, b
    return None


def single_swing(ctx: Context) -> Swing | None:
    f = ctx.finding
    for hand in Color:
        for s in build_swings(ctx.d.notes, ctx.timing)[hand]:
            if abs(s.beat - f.beat_start) < EPS and set(s.notes) == set(f.notes):
                return s
    return None
