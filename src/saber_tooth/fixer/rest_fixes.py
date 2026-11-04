"""Candidate generator for the no-rest rule: thin out the quietest stretch into a rest zone."""

from collections.abc import Iterator

from saber_tooth.analysis import onset_density
from saber_tooth.checks.gaps import REST_BEATS, REST_MAX_NOTES
from saber_tooth.fixer.ops import Delete, Op
from saber_tooth.fixer.verify import Context

MAX_ZONES = 6  # candidate rest windows tried per finding
EPS = 1e-6


def no_rest(ctx: Context) -> Iterator[list[Op]]:
    f, d = ctx.finding, ctx.d
    notes = [n for n in d.notes if f.beat_start - EPS <= n.beat <= f.beat_end + EPS]
    if len(notes) <= REST_MAX_NOTES:
        return
    centre = (f.beat_start + f.beat_end) / 2
    windows = []
    for anchor in notes:
        lo, hi = anchor.beat, anchor.beat + REST_BEATS
        if hi > f.beat_end + EPS:
            break
        inside = [n for n in notes if lo - EPS <= n.beat < hi - EPS]
        quiet = 0.0
        if ctx.analysis is not None:
            quiet = onset_density(
                ctx.analysis, ctx.timing.to_seconds(lo), ctx.timing.to_seconds(hi)
            )
        windows.append((quiet, max(len(inside) - REST_MAX_NOTES, 0), abs(lo + 4 - centre), lo, hi))
    for _, _, _, lo, hi in sorted(windows)[:MAX_ZONES]:
        inside = [n for n in notes if lo - EPS <= n.beat < hi - EPS]
        half = lo + REST_BEATS / 2
        keep = {
            min(inside, key=lambda n: abs(n.beat - lo)),
            min(inside, key=lambda n: abs(n.beat - half)),
        }
        drop = [n for n in inside if n not in keep]
        if drop:
            yield [Delete(d.name, n) for n in drop]
