"""Candidate generators per rule. Each yields op lists in preference order; the caller verifies."""

import math
from collections.abc import Iterator

from saber_tooth.fixer.cells import RING, nearest_cut, occupied, swing_pair
from saber_tooth.fixer.layout_fixes import crossover, note_in_wall, stack_conflict, vision_block
from saber_tooth.fixer.map_fixes import default_environment, empty_gap, missing_difficulty
from saber_tooth.fixer.ops import Delete, Flip, Move, Op
from saber_tooth.fixer.verify import Context, Strategy
from saber_tooth.fixer.wall_fixes import wall_short, wall_trap
from saber_tooth.generator.candidates import build_candidates, phase_of
from saber_tooth.model import OPPOSITE, Cut, Note
from saber_tooth.swings import Swing, build_swings

SCORE_TOLERANCE_BEATS = 0.05


def parity_break(ctx: Context) -> Iterator[list[Op]]:
    pair = swing_pair(ctx)
    if pair is None or pair[0].vector is None:
        return
    a, b = pair
    cuts = {n.cut for n in b.notes}
    if len(cuts) > 1 and Cut.ANY in cuts:
        # arrows mixed with dots: only the arrows turn, each to its own opposite
        yield [Flip(ctx.d.name, n, OPPOSITE[n.cut]) for n in b.notes if n.cut != Cut.ANY]
    base = nearest_cut((-a.vector[0], -a.vector[1]))
    i = RING.index(base)
    for cut in (base, RING[(i - 1) % 8], RING[(i + 1) % 8]):
        ops = [Flip(ctx.d.name, n, cut) for n in b.notes if n.cut != cut]
        if ops:
            yield ops
    yield [Delete(ctx.d.name, n) for n in b.notes]


def wide_jump(ctx: Context) -> Iterator[list[Op]]:
    pair = swing_pair(ctx)
    if pair is None:
        return
    a, b = pair
    now = math.dist(a.end, b.start)
    deltas = [(dx, dy) for dx in range(-3, 4) for dy in range(-2, 3) if (dx, dy) != (0, 0)]
    deltas.sort(
        key=lambda d: (math.hypot(*d), math.dist(a.end, (b.start[0] + d[0], b.start[1] + d[1])))
    )
    taken = occupied(ctx, b.beat, b.notes)
    for dx, dy in deltas:
        # leading notes go first so a sibling's vacated cell is free for the next move
        notes = sorted(b.notes, key=lambda n: -(n.x * dx + n.y * dy))
        cells = [(n.x + dx, n.y + dy) for n in notes]
        if not all(0 <= x < 4 and 0 <= y < 3 for x, y in cells) or taken & set(cells):
            continue
        if math.dist(a.end, (b.start[0] + dx, b.start[1] + dy)) < now:
            yield [Move(ctx.d.name, n, x, y, n.cut) for n, (x, y) in zip(notes, cells, strict=True)]
    yield [Delete(ctx.d.name, n) for n in b.notes]


def _note_score(n: Note, cands) -> float:
    near = [c for c in cands if abs(c.beat - n.beat) <= SCORE_TOLERANCE_BEATS]
    return max([0.0, *(c.score for c in near)])


def _swing_score(ctx: Context, s: Swing, cands) -> float:
    return max([0.0, *(_note_score(n, cands) for n in s.notes)])


def swing_speed(ctx: Context) -> Iterator[list[Op]]:
    pair = swing_pair(ctx)
    if pair is None:
        return
    cands = []
    if ctx.analysis is not None:
        cands = build_candidates(
            ctx.analysis, ctx.timing, ctx.profile, phase_of(ctx.analysis, ctx.timing)
        )[0]
    first, second = pair
    # the lower-scoring swing goes first; a tie removes the later one
    order = (
        [second, first]
        if _swing_score(ctx, second, cands) <= _swing_score(ctx, first, cands)
        else [first, second]
    )
    for s in order:
        if len(s.notes) > 1:
            # the weakest note (a tie: the later one) goes before the whole swing
            single = sorted(s.notes, key=lambda n: (_note_score(n, cands), -n.beat))
            for n in single:
                yield [Delete(ctx.d.name, n)]
        yield [Delete(ctx.d.name, n) for n in s.notes]
    yield from _run_deletes(ctx, first)


def _run_deletes(ctx: Context, first: Swing) -> Iterator[list[Op]]:
    """Runs of one hand's swings: removing one swing of a fast chain only shifts the problem."""
    hand = build_swings(ctx.d.notes, ctx.timing)[first.hand]
    i = next((k for k, s in enumerate(hand) if s.notes == first.notes), None)
    if i is None:
        return
    for size in (2, 3, 4, 5):
        for start in range(max(0, i - size + 2), i + 1):
            window = hand[start : start + size]
            if len(window) == size:
                yield [Delete(ctx.d.name, n) for s in window for n in s.notes]


STRATEGIES: dict[str, Strategy] = {
    "parity-break": parity_break,
    "wide-jump": wide_jump,
    "swing-speed": swing_speed,
    "stack-conflict": stack_conflict,
    "crossover": crossover,
    "vision-block": vision_block,
    "note-in-wall": note_in_wall,
    "empty-gap": empty_gap,
    "wall-trap": wall_trap,
    "wall-short": wall_short,
    "missing-difficulty": missing_difficulty,
    "default-environment": default_environment,
}
