"""Candidate generators for the wall rules: drop the wall the finding points at."""

from collections.abc import Iterator

from saber_tooth.fixer.ops import DeleteWall, Op
from saber_tooth.fixer.verify import Context

EPS = 1e-6


def _offending(ctx: Context) -> Iterator[list[Op]]:
    f = ctx.finding
    for w in ctx.d.walls:
        starts = abs(w.beat - f.beat_start) <= EPS
        if starts and abs(w.beat + w.duration - f.beat_end) <= EPS:
            yield [DeleteWall(ctx.d.name, w)]


def wall_trap(ctx: Context) -> Iterator[list[Op]]:
    yield from _offending(ctx)


def wall_short(ctx: Context) -> Iterator[list[Op]]:
    yield from _offending(ctx)
