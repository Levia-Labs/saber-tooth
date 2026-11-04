"""Candidate generators for the layout rules."""

import itertools
import math
from collections.abc import Iterator

from saber_tooth.fixer.cells import (
    by_distance,
    delete_keeping_parity,
    nearest_cut,
    occupied,
    single_swing,
    step_of,
    swing_of,
)
from saber_tooth.fixer.ops import Delete, Flip, Move, Op, Recolor
from saber_tooth.fixer.verify import Context
from saber_tooth.model import OPPOSITE, Color, Cut, Note


def _in_bounds(x: int, y: int) -> bool:
    return 0 <= x < 4 and 0 <= y < 3


def _swing_cut(anchor: Note, others: list[Note], vector) -> Cut:
    if anchor.cut != Cut.ANY:
        return anchor.cut
    for n in others:
        if n.cut != Cut.ANY:
            return n.cut
    return nearest_cut(vector) if vector else Cut.DOWN


def _pool(anchor: Note, step: tuple[int, int], taken: set) -> list[tuple[int, int]]:
    line = [(anchor.x + k * step[0], anchor.y + k * step[1]) for k in (1, -1)]
    ring = [
        (anchor.x + dx, anchor.y + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if (dx, dy) != (0, 0)
    ]
    ring = sorted(
        (c for c in ring if c not in line), key=lambda c: math.dist(c, (anchor.x, anchor.y))
    )
    return [c for c in [*line, *ring] if _in_bounds(*c) and c not in taken][:6]


def stack_conflict(ctx: Context) -> Iterator[list[Op]]:
    s = single_swing(ctx)
    if s is None:
        return
    name, notes = ctx.d.name, list(s.notes)
    for anchor in notes:
        others = [n for n in notes if n is not anchor]
        cut = _swing_cut(anchor, others, s.vector)
        pool = _pool(anchor, step_of(cut), occupied(ctx, anchor.beat, s.notes))
        plans = list(itertools.permutations(pool, len(others)))
        plans.sort(
            key=lambda p: sum(math.dist(c, (n.x, n.y)) for c, n in zip(p, others, strict=True))
        )
        for cells in plans:
            yield [
                Move(name, n, x, y, n.cut if cut == Cut.ANY else cut)
                for n, (x, y) in zip(others, cells, strict=True)
            ]
    for anchor in notes:
        yield [Delete(name, n) for n in notes if n is not anchor]


def _crosses(r: tuple[int, int], b: tuple[int, int], same_beat: bool) -> bool:
    far = r[0] - b[0] >= 2 and r[0] >= 2 and b[0] <= 1
    return far or (same_beat and r[0] > b[0] and r[1] == b[1])


def crossover(ctx: Context) -> Iterator[list[Op]]:
    f, name = ctx.finding, ctx.d.name
    if len(f.notes) != 2:
        return
    r, b = f.notes
    if r.color != Color.RED:
        r, b = b, r
    yield [Recolor(name, r), Recolor(name, b)]
    flips = [Flip(name, n, OPPOSITE[n.cut]) for n in (r, b) if n.cut != Cut.ANY]
    if flips:
        flipped = [Note(n.beat, n.x, n.y, n.color, OPPOSITE[n.cut], n.angle) for n in (r, b)]
        yield [*flips, *(Recolor(name, n) for n in flipped)]
    later = r if r.beat > b.beat else b
    other = b if later is r else r
    same = abs(r.beat - b.beat) < 1e-6
    taken = occupied(ctx, later.beat, (later,))
    for x, y in by_distance((later.x, later.y)):
        if (x, y) in taken or (x, y) == (later.x, later.y):
            continue
        pair = ((x, y), (other.x, other.y)) if later is r else ((other.x, other.y), (x, y))
        if not _crosses(*pair, same):
            yield [Move(name, later, x, y, later.cut)]
    yield [Delete(name, later)]


def vision_block(ctx: Context) -> Iterator[list[Op]]:
    if not ctx.finding.notes:
        return
    n = ctx.finding.notes[0]
    out = 0 if n.x == 1 else 3
    taken = occupied(ctx, n.beat, (n,))
    first = [(out, 1), (n.x, 0), (out, 0)]
    # every other free cell outside the centre pair, nearest first, before giving the note up
    rest = [
        c for c in by_distance((n.x, n.y)) if c not in first and not (c[0] in (1, 2) and c[1] == 1)
    ]
    for x, y in (*first, *rest):
        if (x, y) not in taken and (x, y) != (n.x, n.y):
            yield [Move(ctx.d.name, n, x, y, n.cut)]
    s = swing_of(ctx, n)
    if s is not None:
        yield from delete_keeping_parity(ctx, s)
        return
    yield [Delete(ctx.d.name, n)]


def in_wall(x: int, y: int, beat: float, w) -> bool:
    return (
        w.x <= x < w.x + w.width
        and w.y <= y < w.y + w.height
        and (w.beat <= beat <= w.beat + w.duration)
    )


def note_in_wall(ctx: Context) -> Iterator[list[Op]]:
    if not ctx.finding.notes:
        return
    n = ctx.finding.notes[0]
    taken = occupied(ctx, n.beat, (n,))
    free = (
        c
        for c in by_distance((n.x, n.y))
        if c not in taken and not any(in_wall(*c, n.beat, w) for w in ctx.d.walls)
    )
    for x, y in itertools.islice(free, 12):
        yield [Move(ctx.d.name, n, x, y, n.cut)]
    yield [Delete(ctx.d.name, n)]


def _weaker(a: Note, b: Note) -> tuple[Note, Note]:
    """(weaker, stronger): a dot gives way to an arrow, otherwise the later note moves."""
    if (a.cut == Cut.ANY) != (b.cut == Cut.ANY):
        return (a, b) if a.cut == Cut.ANY else (b, a)
    return (b, a) if (b.beat, b.color) >= (a.beat, a.color) else (a, b)


def note_converge(ctx: Context) -> Iterator[list[Op]]:
    """Take the weaker note out of the other's flight path; drop it when no cell is free."""
    if len(ctx.finding.notes) != 2:
        return
    weak, strong = _weaker(*ctx.finding.notes)
    name = ctx.d.name
    for mover, other in ((weak, strong), (strong, weak)):
        taken = occupied(ctx, mover.beat, (mover,))
        for x, y in by_distance((mover.x, mover.y)):
            if (x, y) in taken or x == other.x or (x, y) == (mover.x, mover.y):
                continue
            yield [Move(name, mover, x, y, mover.cut)]
    yield [Delete(name, weak)]
    yield [Delete(name, strong)]
