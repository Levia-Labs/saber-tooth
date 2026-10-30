"""Time slices of a difficulty for windowed rule evaluation.

Notes and bombs of a loaded or fixed difficulty are sorted by beat, so a slice is found by
bisection and costs the size of the slice, not of the difficulty.
"""

from bisect import bisect_left, bisect_right
from dataclasses import replace

from saber_tooth.model import Cut, Difficulty


def _beat(x) -> float:
    return x.beat


def beat_range(items: list, lo: float, hi: float) -> tuple[int, int]:
    """Index range [i, j) of the beat-sorted `items` with lo <= beat <= hi."""
    return bisect_left(items, lo, key=_beat), bisect_right(items, hi, key=_beat)


def swing_start(d: Difficulty, lo: float) -> float:
    """Beat of the earliest note a slice from `lo` must keep: each hand's last directional note
    before `lo`, since a dot inherits the last directional swing."""
    start, need = lo, {0, 1}
    for n in reversed(d.notes[: bisect_left(d.notes, lo, key=_beat)]):
        if n.cut != Cut.ANY and int(n.color) in need:
            need.discard(int(n.color))
            start = min(start, n.beat)
            if not need:
                return start
    return float("-inf")  # a hand with no directional note yet: dot parity counts from the start


def slice_difficulty(d: Difficulty, lo: float, hi: float) -> Difficulty:
    """Notes, bombs and walls in [lo, hi], starting at a note that fixes each hand's swing state."""
    start = swing_start(d, lo)
    i, j = beat_range(d.notes, start, hi)
    bi, bj = beat_range(d.bombs, start, hi)
    return replace(
        d,
        notes=d.notes[i:j],
        bombs=d.bombs[bi:bj],
        walls=[w for w in d.walls if w.beat <= hi and w.beat + w.duration >= start],
    )
