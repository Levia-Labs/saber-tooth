"""Swing-speed fixes that keep the music covered: hand a swing over, or delete it and refill the
empty gap the deletion opens. A plain deletion in a sparse difficulty fails the empty-gap check
as soon as the song has audio, so these come before the deletes that do."""

from collections.abc import Iterator
from itertools import islice

from saber_tooth.checks import check_difficulty
from saber_tooth.fixer.cells import occupied
from saber_tooth.fixer.map_fixes import empty_gap
from saber_tooth.fixer.ops import Move, Op, OpConflict, Recolor, apply_ops
from saber_tooth.fixer.verify import Context, accepts, map_timing
from saber_tooth.model import Cut, Note
from saber_tooth.swings import Swing

FILL_TRIES = 6
MIRROR_CUT = {
    Cut.LEFT: Cut.RIGHT,
    Cut.RIGHT: Cut.LEFT,
    Cut.UP_LEFT: Cut.UP_RIGHT,
    Cut.UP_RIGHT: Cut.UP_LEFT,
    Cut.DOWN_LEFT: Cut.DOWN_RIGHT,
    Cut.DOWN_RIGHT: Cut.DOWN_LEFT,
}


def hand_over(ctx: Context, s: Swing) -> Iterator[list[Op]]:
    """Give the swing to the other hand: as it is, then mirrored across the grid so the notes
    sit on the new hand's side. The checks decide whether the other hand is free there."""
    name = ctx.d.name
    yield [Recolor(name, n) for n in s.notes]
    moved = [
        Note(n.beat, 3 - n.x, n.y, n.color, MIRROR_CUT.get(n.cut, n.cut), n.angle) for n in s.notes
    ]
    if all(m.x != n.x for m, n in zip(moved, s.notes, strict=True)) and not occupied(
        ctx, s.beat, s.notes
    ) & {(m.x, m.y) for m in moved}:
        yield [
            *(Move(name, n, m.x, m.y, m.cut) for n, m in zip(s.notes, moved, strict=True)),
            *(Recolor(name, m) for m in moved),
        ]


def delete_and_refill(ctx: Context, plan: list[Op]) -> list[Op] | None:
    """`plan` (deletions) plus a verified fill for each empty-gap it opens, or None when a gap
    stays open."""
    if ctx.analysis is None:
        return None
    try:
        fixed = apply_ops(ctx.beatmap, plan)
    except OpConflict:
        return None
    name = ctx.d.name
    lo = min(op.note.beat for op in plan) - ctx.profile.gap_beats
    hi = max(op.note.beat for op in plan) + ctx.profile.gap_beats
    out = list(plan)
    for _ in range(3):
        d = fixed.difficulties[name]
        gaps = [
            g
            for g in check_difficulty(d, map_timing(fixed, d), ctx.profile, ctx.analysis)
            if g.rule == "empty-gap" and g.beat_end >= lo and g.beat_start <= hi
        ]
        if not gaps:
            return out
        gctx = Context(fixed, gaps[0], ctx.analysis, ctx.templates, ctx.seed)
        for ops in islice(empty_gap(gctx), FILL_TRIES):
            filled = accepts(gctx, ops)
            if filled is not None:
                fixed, out = filled, out + ops
                break
        else:
            return None
    return None
