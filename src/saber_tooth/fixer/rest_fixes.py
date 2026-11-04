"""Candidate generator for the no-rest rule: thin out quiet stretches into rest zones."""

import math
from bisect import bisect_left
from collections.abc import Iterator

from saber_tooth.analysis import onset_density
from saber_tooth.checks.gaps import DEFAULT_REST_SPAN_S, REST_BEATS, REST_MAX_NOTES, REST_SPAN_S
from saber_tooth.fixer.ops import Delete, Op
from saber_tooth.fixer.verify import Context

MAX_VARIANTS = 6  # candidate rest-zone sets tried per finding
SPAN_SHARE = 0.7  # the pieces of play left between zones average this share of the span
MAX_ZONES = 40
EPS = 1e-6


def _zone_plan(ctx: Context) -> tuple[int, float]:
    """(zones, slot radius in beats): enough rest zones that, wherever each sits inside its
    slot, every piece of play left between them stays shorter than the tier's span."""
    f, t = ctx.finding, ctx.timing
    seconds = t.to_seconds(f.beat_end) - t.to_seconds(f.beat_start)
    span = REST_SPAN_S.get(f.difficulty, DEFAULT_REST_SPAN_S)
    beats = f.beat_end - f.beat_start
    zones = max(1, math.ceil(seconds / (span * SPAN_SHARE)) - 1)
    while True:
        piece_s = seconds / (zones + 1)
        radius = beats / (zones + 1) * (span / piece_s - 1) / 2
        if radius >= REST_BEATS or zones >= MAX_ZONES:
            return zones, max(radius, REST_BEATS / 2)
        zones += 1


def _slot_windows(ctx: Context, notes, lo: float, hi: float, centre: float) -> list[tuple]:
    """Rest windows anchored on a note inside [lo, hi - REST_BEATS], quietest first."""
    beats = [n.beat for n in notes]  # sorted: the notes of a difficulty are
    windows = []
    for anchor in notes:
        a, b = anchor.beat, anchor.beat + REST_BEATS
        if a < lo - EPS:
            continue
        if b > hi + EPS:
            break
        count = bisect_left(beats, b - EPS) - bisect_left(beats, a - EPS)
        quiet = 0.0
        if ctx.analysis is not None:
            quiet = onset_density(ctx.analysis, ctx.timing.to_seconds(a), ctx.timing.to_seconds(b))
        windows.append((quiet, max(count - REST_MAX_NOTES, 0), abs(a + 4 - centre), a, b))
    return sorted(windows)


def _drops(notes, a: float, b: float) -> list:
    inside = [n for n in notes if a - EPS <= n.beat < b - EPS]
    half = a + REST_BEATS / 2
    keep = {
        min(inside, key=lambda n: abs(n.beat - a)),
        min(inside, key=lambda n: abs(n.beat - half)),
    }
    return [n for n in inside if n not in keep]


def no_rest(ctx: Context) -> Iterator[list[Op]]:
    f, d = ctx.finding, ctx.d
    notes = [n for n in d.notes if f.beat_start - EPS <= n.beat <= f.beat_end + EPS]
    if len(notes) <= REST_MAX_NOTES:
        return
    zones, radius = _zone_plan(ctx)
    width = (f.beat_end - f.beat_start) / (zones + 1)
    slots = []
    for i in range(zones):
        centre = f.beat_start + (i + 1) * width
        lo = max(centre - radius, f.beat_start)
        hi = min(centre + radius, f.beat_end)
        slots.append(_slot_windows(ctx, notes, lo, hi, centre))
    seen = set()
    for variant in range(MAX_VARIANTS):
        picks = tuple(w[min(variant, len(w) - 1)][3:5] for w in slots if w)
        if not picks or picks in seen:
            continue
        seen.add(picks)
        drop = [n for a, b in picks for n in _drops(notes, a, b)]
        if drop:
            yield [Delete(d.name, n) for n in drop]
