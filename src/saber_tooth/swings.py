import math
from dataclasses import dataclass
from itertools import combinations

from saber_tooth.model import CUT_VECTORS, Color, Cut, Note
from saber_tooth.timing import Timing

Vec = tuple[float, float]
MAX_CUT_ANGLE = 45.5  # 45 degrees plus tolerance for the rounded diagonal vectors
DEFAULT_PREV: Vec = CUT_VECTORS[Cut.UP]  # opposite of this is DOWN, the first swing's default


@dataclass(frozen=True)
class Swing:
    hand: Color
    beat: float
    seconds: float
    notes: tuple[Note, ...]
    vector: Vec | None
    start: tuple[float, float]
    end: tuple[float, float]


def angle_between(u: Vec, v: Vec) -> float:
    cos = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def _cut_vector(notes: list[Note]) -> tuple[Vec | None, bool]:
    """Return (mean cut vector, conflict). Vector is None when every note is ANY."""
    vecs = [CUT_VECTORS[n.cut] for n in notes if n.cut != Cut.ANY]
    if any(angle_between(u, v) > MAX_CUT_ANGLE for u, v in combinations(vecs, 2)):
        return None, True
    if not vecs:
        return None, False
    mx = sum(v[0] for v in vecs) / len(vecs)
    my = sum(v[1] for v in vecs) / len(vecs)
    if len(set(vecs)) == 1:
        return vecs[0], False
    norm = math.hypot(mx, my)
    return (mx / norm, my / norm), False


def _group(notes: list[Note], timing: Timing, window_s: float) -> list[list[Note]]:
    groups: list[list[Note]] = []
    first_s = 0.0
    for n in sorted(notes):
        s = timing.to_seconds(n.beat)
        if groups and s - first_s <= window_s:
            groups[-1].append(n)
        else:
            groups.append([n])
            first_s = s
    return groups


def build_swings(
    notes: list[Note],
    timing: Timing,
    window_s: float = 0.02,
) -> dict[Color, list[Swing]]:
    out: dict[Color, list[Swing]] = {Color.RED: [], Color.BLUE: []}
    for hand in (Color.RED, Color.BLUE):
        prev: Vec = DEFAULT_PREV
        for group in _group([n for n in notes if n.color == hand], timing, window_s):
            cut, conflict = _cut_vector(group)
            if conflict:
                vector: Vec | None = None
                prev = DEFAULT_PREV  # last direction unknown: the next ANY swing goes DOWN
            elif cut is None:
                vector = (-prev[0], -prev[1])
            else:
                vector = cut
            if vector is not None:
                prev = vector
                ordered = sorted(group, key=lambda n: n.x * vector[0] + n.y * vector[1])
            else:
                ordered = sorted(group, key=lambda n: (n.x, n.y))
            out[hand].append(
                Swing(
                    hand,
                    group[0].beat,
                    timing.to_seconds(group[0].beat),
                    tuple(group),
                    vector,
                    (ordered[0].x, ordered[0].y),
                    (ordered[-1].x, ordered[-1].y),
                )
            )
    return out
