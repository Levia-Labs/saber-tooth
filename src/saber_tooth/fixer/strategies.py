"""Candidate generators per rule. Each yields op lists in preference order; the caller verifies."""

import math
from collections.abc import Iterator
from itertools import product

from saber_tooth.checks import LOCAL_REACH_S
from saber_tooth.fixer import window
from saber_tooth.fixer.cells import (
    EPS,
    RING,
    delete_keeping_parity,
    nearest_cut,
    occupied,
    swing_pair,
)
from saber_tooth.fixer.layout_fixes import (
    crossover,
    note_converge,
    note_in_wall,
    stack_conflict,
    vision_block,
)
from saber_tooth.fixer.map_fixes import (
    default_environment,
    empty_gap,
    light_strobe,
    missing_difficulty,
)
from saber_tooth.fixer.ops import Delete, Flip, Move, Op
from saber_tooth.fixer.rest_fixes import no_rest
from saber_tooth.fixer.swing_fixes import delete_and_refill, hand_over
from saber_tooth.fixer.verify import Context, Strategy
from saber_tooth.fixer.wall_fixes import wall_short, wall_trap
from saber_tooth.generator.candidates import build_candidates, phase_of
from saber_tooth.model import OPPOSITE, Cut, Note
from saber_tooth.swings import Swing

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
    yield [Delete(ctx.d.name, n) for n in b.notes]  # a, c already alternate once b is gone


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
    for dx, dy in deltas:
        if math.dist(a.end, (b.start[0] + dx, b.start[1] + dy)) < now:
            ops = _shift_swings(ctx, [b], dx, dy)
            if ops:
                yield ops
    yield from _joint_shifts(ctx, a, b, deltas)
    yield from delete_keeping_parity(ctx, b)


def _shift_swings(ctx: Context, run: list[Swing], dx: int, dy: int) -> list[Op] | None:
    """Moves shifting every note of the swings by (dx, dy), or None when one leaves the grid
    or lands on a cell another note holds at its beat."""
    ops: list[Op] = []
    for s in run:
        taken = occupied(ctx, s.beat, s.notes)
        # leading notes go first so a sibling's vacated cell is free for the next move
        notes = sorted(s.notes, key=lambda n: -(n.x * dx + n.y * dy))
        cells = [(n.x + dx, n.y + dy) for n in notes]
        if not all(0 <= x < 4 and 0 <= y < 3 for x, y in cells) or taken & set(cells):
            return None
        ops += [Move(ctx.d.name, n, x, y, n.cut) for n, (x, y) in zip(notes, cells, strict=True)]
    return ops


def _joint_shifts(ctx: Context, a: Swing, b: Swing, deltas) -> Iterator[list[Op]]:
    """Move b together with the swings after it, each by its own step. Moving b alone only hands
    the jump to the pair (b, c); a window of consecutive swings is moved jointly, ordered by
    the fastest hand travel left in the window, and only plans that beat the current jump go
    on to verification."""
    reach = ctx.timing.to_beats(2 * LOCAL_REACH_S) - ctx.timing.to_beats(0.0)
    wide = window.swings_near(ctx.d, ctx.timing, b.beat, b.beat + reach)
    chain = [a, b]
    for s in [x for x in wide[b.hand] if x.beat > b.beat + EPS][:2]:
        if s.seconds - chain[-1].seconds > LOCAL_REACH_S:
            break
        chain.append(s)

    def speed(u: Swing, v: Swing, du, dv) -> float:
        dist = math.dist(
            (u.end[0] + du[0], u.end[1] + du[1]), (v.start[0] + dv[0], v.start[1] + dv[1])
        )
        return dist / max(v.seconds - u.seconds, 1e-6)

    now = speed(a, b, (0, 0), (0, 0))
    steps = [(0, 0), *(d for d in deltas if math.hypot(*d) <= 2.3)]
    for width in range(2, len(chain)):
        run = chain[1 : 1 + width]
        small = [d for d in steps if width == 2 or math.hypot(*d) <= 1.5]
        plans = []
        for combo in product(small, repeat=width):
            if combo[0] == (0, 0):
                continue
            pairs = zip(chain, chain[1:], [(0, 0), *combo], combo, strict=False)
            worst = max(speed(u, v, du, dv) for u, v, du, dv in pairs)
            if worst < now:
                plans.append((worst, sum(math.hypot(*d) for d in combo), combo))
        for _, _, combo in sorted(plans):
            ops: list[Op] = []
            for s, (dx, dy) in zip(run, combo, strict=True):
                got = _shift_swings(ctx, [s], dx, dy) if (dx, dy) != (0, 0) else []
                if got is None:
                    break
                ops += got
            else:
                yield ops


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
        yield from hand_over(ctx, s)  # keeps every note: deleting one can open an empty-gap
    for s in order:
        if len(s.notes) > 1:
            # the weakest note (a tie: the later one) goes before the whole swing
            single = sorted(s.notes, key=lambda n: (_note_score(n, cands), -n.beat))
            for n in single:
                yield [Delete(ctx.d.name, n)]
        yield [Delete(ctx.d.name, n) for n in s.notes]
    yield from _run_deletes(ctx, first)
    for s in order:  # last: the deletion that opens a gap, with the gap refilled
        refilled = delete_and_refill(ctx, [Delete(ctx.d.name, n) for n in s.notes])
        if refilled:
            yield refilled


def _run_deletes(ctx: Context, first: Swing) -> Iterator[list[Op]]:
    """Runs of one hand's swings: removing one swing of a fast chain only shifts the problem."""
    hand = ctx.swings()[first.hand]
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
    "note-converge": note_converge,
    "empty-gap": empty_gap,
    "no-rest": no_rest,
    "wall-trap": wall_trap,
    "wall-short": wall_short,
    "missing-difficulty": missing_difficulty,
    "default-environment": default_environment,
    "light-strobe": light_strobe,
}
