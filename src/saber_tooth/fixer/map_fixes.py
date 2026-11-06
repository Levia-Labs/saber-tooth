"""Candidate generators for map-level and gap findings."""

import contextlib
import copy
import math
from collections.abc import Iterator

from saber_tooth.checks.constants import SLIDER_S
from saber_tooth.fixer.cells import EPS
from saber_tooth.fixer.gap_fill import fill_hand, fill_notes, fill_slots, trim_for_exit
from saber_tooth.fixer.ops import AddDifficulty, ApplyLightshow, Fill, Op
from saber_tooth.fixer.thin import thin
from saber_tooth.fixer.verify import Context, map_timing
from saber_tooth.generator import GenerationError, generate_difficulty
from saber_tooth.lightshow import build_lightshow
from saber_tooth.lightshow.pacing import pace_show
from saber_tooth.mapio.write import BOX_KEYS, FX_KEY
from saber_tooth.model import DIFFICULTIES, Color, Cut, Note
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
    swings = build_swings(d.notes, timing, SLIDER_S)
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
        made = None
    if made is not None:
        yield from _generated(ctx, made, start, end)
    yield from _patterned(ctx, swings, entry)


def _exit_chain(hand_swings: list, end: float) -> tuple[int, tuple[float, float] | None]:
    """Dot swings after the gap inherit the direction before them: count them up to the first
    arrow swing and return its vector."""
    flips = 0
    for s in (s for s in hand_swings if s.beat >= end - EPS):
        if s.vector is None:
            return flips, None
        if all(n.cut == Cut.ANY for n in s.notes):
            flips += 1
            continue
        return flips, s.vector
    return flips, None


def _counts(ctx: Context, start: float, end: float, spacing: float) -> list[int]:
    profile, length = ctx.profile, end - start
    least = max(1, math.ceil(length / (profile.gap_beats - profile.grid)) - 1)
    seconds = ctx.timing.to_seconds(end) - ctx.timing.to_seconds(start)
    most = max(least, min(int(length / spacing) - 1, round(profile.target_nps * seconds)))
    density = _neighbour_density(ctx, start, end)
    mid = least if density is None else round(density * length)
    wanted = [min(max(mid, least), most), least, most, (least + most) // 2]
    return list(dict.fromkeys(wanted))


def _patterned(ctx: Context, swings: dict, entry: dict) -> Iterator[list[Op]]:
    """Pure fallback fill: a sparse and a dense onset-aligned pattern that turns each hand
    opposite to its swing before the gap and clear of the swing after it."""
    d, f, timing, profile = ctx.d, ctx.finding, ctx.timing, ctx.profile
    start, end = f.beat_start, f.beat_end
    spacing = max(
        profile.grid,
        timing.to_beats(timing.to_seconds(start) + profile.warn.min_hand_gap_s) - start,
    )
    onsets = sorted(
        timing.to_beats(t)
        for t in (*ctx.analysis.beats, *ctx.analysis.kick, *ctx.analysis.snare)
        if start <= timing.to_beats(t) <= end
    )
    vectors = {h: (s[0].vector if s else None) for h, s in entry.items()}
    last = max((s[0] for s in entry.values() if s), key=lambda s: s.seconds, default=None)
    first = Color(1 - int(last.hand)) if last else Color.RED
    exits = {h: _exit_chain(ss, end) for h, ss in swings.items()}
    used = {n.beat for n in d.notes}
    for count in _counts(ctx, start, end, spacing):
        slots = fill_slots(start, end, profile.grid, spacing, count, onsets)
        if slots is None or any(abs(b - u) < EPS for b in slots for u in used):
            continue
        notes = trim_for_exit(fill_notes(slots, first, vectors), exits)
        if notes:
            yield [Fill(d.name, start, end, tuple(notes))]
    # last: a pair of one hand's notes leaves a rest zone (at most two notes) and both hands'
    # alternation intact, for a gap that is the map's only rest
    for hand in (first, Color(1 - int(first))):
        slots = fill_slots(start, end, profile.grid, spacing, 2, onsets)
        if slots is None or any(abs(b - u) < EPS for b in slots for u in used):
            break
        notes = fill_hand(slots, hand, vectors)
        if trim_for_exit(notes, exits) == notes:
            yield [Fill(d.name, start, end, tuple(notes))]


def _generated(ctx: Context, made, start: float, end: float) -> Iterator[list[Op]]:
    d = ctx.d
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


def light_strobe(ctx: Context) -> Iterator[list[Op]]:
    d, info = ctx.d, ctx.beatmap.info
    if d is None:
        ctx.reason = f"difficulty {ctx.finding.difficulty} not found"
        return
    groups = {k: copy.deepcopy(d.raw[k]) for k in (*BOX_KEYS, FX_KEY) if k in d.raw}
    events, kept = pace_show(list(d.events), groups, ctx.timing)
    groups.update(kept)
    show = (events, list(d.boosts), groups)
    yield [ApplyLightshow(info.environment, info.color_scheme, {d.name: show})]
