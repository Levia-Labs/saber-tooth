"""Candidate generators for map-level and gap findings."""

import contextlib
import math
from collections.abc import Iterator

from saber_tooth.fixer.cells import EPS
from saber_tooth.fixer.ops import AddDifficulty, ApplyLightshow, Fill, Op
from saber_tooth.fixer.thin import thin
from saber_tooth.fixer.verify import Context, map_timing
from saber_tooth.generator import GenerationError, generate_difficulty
from saber_tooth.lightshow import build_lightshow
from saber_tooth.model import DIFFICULTIES, Note
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing

DENSITY_SPAN = 8.0
CAP_SLACK = 1.5


def _spread(notes: list[Note], count: int) -> list[Note]:
    if count >= len(notes):
        return notes
    if count <= 1:
        return notes[:1]
    return [notes[round(i * (len(notes) - 1) / (count - 1))] for i in range(count)]


def _neighbour_density(ctx: Context, start: float, end: float) -> float | None:
    beats = sorted(n.beat for n in ctx.d.notes)
    sides = []
    if start - DENSITY_SPAN >= 0:
        sides.append(sum(1 for b in beats if start - DENSITY_SPAN <= b < start))
    sides.append(sum(1 for b in beats if end <= b < end + DENSITY_SPAN))
    return sum(sides) / len(sides) / DENSITY_SPAN if sides else None


def empty_gap(ctx: Context) -> Iterator[list[Op]]:
    if ctx.analysis is None or ctx.profile is None:
        ctx.reason = "needs analysis"
        return
    d, f, timing = ctx.d, ctx.finding, ctx.timing
    start, end = f.beat_start, f.beat_end
    swings = build_swings(d.notes, timing)
    entry = {h: [s for s in ss if s.beat <= start + EPS][-1:] for h, ss in swings.items()}
    after = {h: [s for s in ss if s.beat >= end - EPS][:1] for h, ss in swings.items()}
    window = (timing.to_seconds(start), timing.to_seconds(end))
    try:
        made = generate_difficulty(
            ctx.analysis,
            timing,
            ctx.profile,
            ctx.seed,
            window=window,
            entry={h: s[0] for h, s in entry.items() if s},
            exit={h: s[0] for h, s in after.items() if s},
            walls=d.walls,
        )
    except GenerationError:
        return
    used = {n.beat for n in d.notes}
    new = [
        n
        for n in made.notes
        if start - EPS <= n.beat <= end + EPS and not any(abs(n.beat - b) < EPS for b in used)
    ]
    if not new:
        return
    removed = tuple(w for w in d.walls if w not in made.walls)
    added = tuple(w for w in made.walls if w not in d.walls)
    density = _neighbour_density(ctx, start, end)
    if density is not None:
        cap = max(1, math.ceil(density * (end - start)))
        if len(new) > cap * CAP_SLACK:
            yield [Fill(d.name, start, end, tuple(_spread(new, cap)), added, removed)]
    yield [Fill(d.name, start, end, tuple(new), added, removed)]
    if added or removed:
        yield [Fill(d.name, start, end, tuple(new))]


def _denser(ctx: Context):
    name = ctx.finding.difficulty
    above = DIFFICULTIES[DIFFICULTIES.index(name) + 1 :] if name in DIFFICULTIES else ()
    return next((ctx.beatmap.difficulties[n] for n in above if n in ctx.beatmap.difficulties), None)


def missing_difficulty(ctx: Context) -> Iterator[list[Op]]:
    profile = PROFILES.get(ctx.finding.difficulty)
    if profile is None:
        return
    timing = map_timing(ctx.beatmap)
    if ctx.analysis is not None:
        with contextlib.suppress(GenerationError):
            generated = generate_difficulty(ctx.analysis, timing, profile, ctx.seed)
            yield [AddDifficulty(generated)]
    source = _denser(ctx)
    if source is None:
        ctx.reason = "needs analysis"
        return
    thinned = thin(source, profile, Timing(ctx.beatmap.info.bpm, source.bpm_events))
    if thinned is None:
        ctx.reason = "thinned difficulty could not be made finding-free"
        return
    yield [AddDifficulty(thinned)]


def default_environment(ctx: Context) -> Iterator[list[Op]]:
    t = ctx.templates
    if t is None or not any(t.units.values()):
        ctx.reason = "no lightshow templates"
        return
    try:
        payload = build_lightshow(ctx.beatmap, map_timing(ctx.beatmap), t, ctx.analysis, ctx.seed)
    except ValueError as e:
        ctx.reason = str(e) or "no lightshow templates"
        return
    yield [ApplyLightshow.from_payload(payload)]
