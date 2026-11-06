"""Pure fill pattern for an empty gap: grid slots on the song's onsets, then notes whose cuts
alternate per hand, continuing the swing before the gap and leading into the swing after it."""

import math
from bisect import bisect_left
from collections.abc import Mapping, Sequence

from saber_tooth.checks.constants import PARITY_DOT
from saber_tooth.fixer.cells import nearest_cut
from saber_tooth.model import CUT_VECTORS, OPPOSITE, Color, Cut, Note

Vec = tuple[float, float]
EPS = 1e-6
LANES = {Color.RED: 1, Color.BLUE: 2}  # inner lanes: red left, blue right, never crossing
LAYER = 1


def _near(onsets: Sequence[float], b: float) -> float:
    i = bisect_left(onsets, b)
    return min((abs(onsets[j] - b) for j in (i - 1, i) if 0 <= j < len(onsets)), default=math.inf)


def fill_slots(
    start: float,
    end: float,
    grid: float,
    spacing: float,
    count: int,
    onsets: Sequence[float] = (),
) -> list[float] | None:
    """`count` grid beats strictly inside (start, end), at least `spacing` apart, spread evenly
    and pulled to onsets (sorted beats) where one sits within half a grid step; None if they do
    not fit."""
    if count < 1 or end <= start or grid <= 0:
        return None
    lo, hi = math.floor(start / grid + EPS) + 1, math.ceil(end / grid - EPS) - 1
    slots = [k * grid for k in range(lo, hi + 1)]
    out: list[float] = []
    for i in range(count):
        ideal = start + (end - start) * (i + 1) / (count + 1)
        floor = out[-1] + spacing - EPS if out else -math.inf
        ceil = end - spacing * (count - 1 - i) if count - 1 - i else math.inf
        fits = [b for b in slots if b >= floor and b <= ceil + EPS and start < b < end]
        if not fits:
            return None
        out.append(min(fits, key=lambda b: (_near(onsets, b) > grid / 2, abs(b - ideal))))
    return out


def _cut_for(vec: Vec | None) -> Cut:
    return Cut.DOWN if vec is None else OPPOSITE[nearest_cut(vec)]


def fill_notes(
    beats: Sequence[float],
    first_hand: Color,
    entry: Mapping[Color, Vec | None],
    lanes: Mapping[Color, int] = LANES,
) -> list[Note]:
    """Notes on `beats`, hands alternating from `first_hand`; each hand's cuts turn opposite to
    its previous swing (`entry` vectors, None when unknown)."""
    hands = [first_hand, Color(1 - int(first_hand))]
    cut = {h: _cut_for(entry.get(h)) for h in Color}
    out = []
    for i, b in enumerate(beats):
        h = hands[i % 2]
        out.append(Note(b, lanes[h], LAYER, h, cut[h]))
        cut[h] = OPPOSITE[cut[h]]
    return out


def fill_hand(beats: Sequence[float], hand: Color, entry: Mapping[Color, Vec | None]) -> list[Note]:
    """Notes of one hand on `beats`, its cuts turning opposite to its swing before the gap: an
    even count leaves both hands' alternation as it was, with at most two notes in the gap."""
    cut = _cut_for(entry.get(hand))
    out = []
    for b in beats:
        out.append(Note(b, LANES[hand], LAYER, hand, cut))
        cut = OPPOSITE[cut]
    return out


def fits_exit(notes: Sequence[Note], hand: Color, flips: int, nxt: Vec | None) -> bool:
    """The hand's last fill swing, seen through `flips` dot swings, must not repeat the
    direction of the first arrow swing `nxt` after the gap."""
    mine = [n for n in notes if n.color == hand]
    if nxt is None or not mine:
        return True
    last = CUT_VECTORS[mine[-1].cut]
    sign = -1 if flips % 2 else 1
    return sign * (last[0] * nxt[0] + last[1] * nxt[1]) <= PARITY_DOT


def trim_for_exit(
    notes: list[Note], exits: Mapping[Color, tuple[int, Vec | None]]
) -> list[Note] | None:
    """Drop a hand's last note when it would repeat the direction after the gap; None if that
    does not settle it."""
    out = list(notes)
    for hand, (flips, nxt) in exits.items():
        if fits_exit(out, hand, flips, nxt):
            continue
        last = max((n for n in out if n.color == hand), key=lambda n: n.beat)
        out.remove(last)
        if not fits_exit(out, hand, flips, nxt):
            return None
    return out
