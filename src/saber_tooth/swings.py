from dataclasses import dataclass

from saber_tooth.model import CUT_VECTORS, Color, Cut, Note
from saber_tooth.timing import Timing

Vec = tuple[float, float]
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


def _cut_vector(notes: list[Note]) -> tuple[Cut | None, bool]:
    """Return (shared cut, conflict). Cut is None when every note is ANY."""
    cuts = {n.cut for n in notes if n.cut != Cut.ANY}
    if len(cuts) > 1:
        return None, True
    return (next(iter(cuts)) if cuts else None), False


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
                vector = CUT_VECTORS[cut]
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
