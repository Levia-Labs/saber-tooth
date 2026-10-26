import random

from saber_tooth.model import Color, Cut

Step = tuple[Cut, int, int]
C = Cut

_H = {
    C.LEFT: C.RIGHT,
    C.RIGHT: C.LEFT,
    C.UP_LEFT: C.UP_RIGHT,
    C.UP_RIGHT: C.UP_LEFT,
    C.DOWN_LEFT: C.DOWN_RIGHT,
    C.DOWN_RIGHT: C.DOWN_LEFT,
    C.UP: C.UP,
    C.DOWN: C.DOWN,
}
_V = {
    C.UP: C.DOWN,
    C.DOWN: C.UP,
    C.UP_LEFT: C.DOWN_LEFT,
    C.DOWN_LEFT: C.UP_LEFT,
    C.UP_RIGHT: C.DOWN_RIGHT,
    C.DOWN_RIGHT: C.UP_RIGHT,
    C.LEFT: C.LEFT,
    C.RIGHT: C.RIGHT,
}
# Every motif alternates swing direction (dot < 0), wrap-around included; red uses columns 0-1.
RED_MOTIFS: tuple[tuple[Step, ...], ...] = (
    ((C.DOWN, 1, 0), (C.UP, 1, 0), (C.DOWN_LEFT, 0, 0), (C.UP_RIGHT, 0, 1)),
    ((C.DOWN, 1, 0), (C.UP_LEFT, 0, 1), (C.DOWN_RIGHT, 1, 0), (C.UP, 1, 0)),
    ((C.DOWN_LEFT, 1, 0), (C.UP_RIGHT, 0, 1), (C.DOWN, 1, 0), (C.UP, 0, 0)),
    ((C.DOWN, 1, 0), (C.UP, 0, 0), (C.DOWN, 1, 0), (C.UP_LEFT, 0, 1)),
    ((C.DOWN_RIGHT, 1, 0), (C.UP_LEFT, 0, 1), (C.DOWN_RIGHT, 1, 0), (C.UP_LEFT, 0, 1)),
    ((C.DOWN, 0, 0), (C.UP, 0, 0), (C.DOWN, 1, 0), (C.UP_RIGHT, 0, 1)),
    ((C.DOWN, 1, 0), (C.UP_RIGHT, 0, 1), (C.DOWN_LEFT, 0, 0), (C.UP, 0, 0)),
    ((C.DOWN, 1, 0), (C.UP, 1, 0), (C.DOWN, 1, 0), (C.UP, 1, 0)),
    ((C.DOWN_RIGHT, 0, 0), (C.UP_LEFT, 0, 1), (C.DOWN, 1, 0), (C.UP, 1, 0)),
    # top row, sweeps and sideways swings at the outer column
    ((C.DOWN, 1, 2), (C.UP, 1, 0), (C.DOWN, 0, 2), (C.UP, 0, 0)),
    ((C.DOWN_RIGHT, 0, 2), (C.UP_LEFT, 0, 1), (C.DOWN_RIGHT, 1, 0), (C.UP, 1, 0)),
    ((C.RIGHT, 0, 1), (C.LEFT, 0, 0), (C.RIGHT, 0, 2), (C.LEFT, 0, 1)),
    ((C.DOWN, 1, 0), (C.UP_LEFT, 0, 2), (C.DOWN_RIGHT, 1, 0), (C.UP, 1, 2)),
    ((C.DOWN, 1, 0), (C.UP_LEFT, 0, 2), (C.DOWN, 0, 0), (C.UP_RIGHT, 1, 2)),
    ((C.DOWN, 0, 2), (C.UP_RIGHT, 0, 1), (C.DOWN_LEFT, 0, 0), (C.UP, 1, 0)),
    ((C.DOWN, 1, 0), (C.UP, 1, 0), (C.DOWN, 1, 0), (C.UP_RIGHT, 1, 2)),
    ((C.DOWN_LEFT, 0, 1), (C.UP_RIGHT, 1, 2), (C.DOWN_LEFT, 0, 1), (C.UP_RIGHT, 1, 2)),
    ((C.DOWN, 0, 2), (C.UP, 0, 1), (C.DOWN, 1, 2), (C.UP, 1, 0)),
    ((C.LEFT, 1, 2), (C.RIGHT, 0, 2), (C.LEFT, 1, 0), (C.RIGHT, 0, 0)),
)
LATTICE_CUTS = (C.UP, C.DOWN, C.UP_LEFT, C.UP_RIGHT, C.DOWN_LEFT, C.DOWN_RIGHT)


def mirror_h(step: Step) -> Step:
    cut, x, y = step
    return (_H[cut], 3 - x, y)


def flip_v(step: Step) -> Step:
    cut, x, y = step
    return (_V[cut], x, y)


BLUE_MOTIFS = tuple(tuple(mirror_h(s) for s in m) for m in RED_MOTIFS)


def motif_count() -> int:
    return len(RED_MOTIFS)


def motif_steps(hand: Color, index: int, flipped: bool) -> tuple[Step, ...]:
    steps = (RED_MOTIFS if hand == Color.RED else BLUE_MOTIFS)[index]
    return tuple(flip_v(s) for s in steps) if flipped else steps


def _weight(motif: tuple[Step, ...]) -> float:
    """Favour motifs that spread over diagonals, sideways swings and the top row."""
    vertical = sum(1 for cut, _, _ in motif if cut in (C.UP, C.DOWN))
    inner_bottom = sum(1 for _, x, y in motif if x in (1, 2) and y == 0)
    return (1.0, 1.0, 1.0, 0.5, 0.2)[vertical] / (1 + 0.5 * inner_bottom)


_WEIGHTS = tuple(_weight(m) for m in RED_MOTIFS)


def _draw(seed: int, phrase: int, exclude: dict[Color, int] | None = None) -> dict[Color, int]:
    rng = random.Random(seed + phrase)  # noqa: S311 # nosec B311 - musical variety, not security
    picks = {}
    for hand in (Color.RED, Color.BLUE):
        weights = list(_WEIGHTS)
        if exclude is not None:
            weights[exclude[hand]] = 0.0  # never repeat the previous phrase's motif
        picks[hand] = rng.choices(range(len(weights)), weights)[0]
    return picks


def phrase_picks(seed: int, phrase: int) -> dict[Color, int]:
    return _draw(seed, phrase, _draw(seed, phrase - 1))


def pool(hand: Color) -> list[Step]:
    seen: dict[Step, None] = {}
    for i in range(len(RED_MOTIFS)):
        for flipped in (False, True):
            for step in motif_steps(hand, i, flipped):
                seen[step] = None
    return list(seen)


def lattice(hand: Color) -> list[Step]:
    cols = (0, 1) if hand == Color.RED else (2, 3)
    return [(c, x, y) for c in LATTICE_CUTS for x in cols for y in range(3)]
