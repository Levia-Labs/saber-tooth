"""Crop a Beatmap to a beat window: shift, trim, lead-in and light fades. Pure: no files."""

import copy
import math
from collections.abc import Callable
from dataclasses import dataclass, replace

from saber_tooth.crop.nps import note_beats
from saber_tooth.crop.phrases import grid_events, tempo_at
from saber_tooth.lightshow.units import BAR
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import BasicEvent, Beatmap, BpmEvent, Difficulty, Wall
from saber_tooth.timing import Timing

LEAD_IN_S = 2.0
LIGHT_TYPES = (0, 1, 2, 3, 4)
FADE_LEVELS = (0.25, 0.5, 0.75, 1.0)
FADE_STEP_BEATS = 0.25
SLIDER_KEYS = ("sliders", "burstSliders")
COLOR_GROUPS = "lightColorEventBoxGroups"

Shift = Callable[[float], float]


@dataclass(frozen=True)
class Cropped:
    beatmap: Beatmap
    start_s: float
    length_s: float
    lead_s: float
    fade_out_s: float


def _inside(beat: float, start: float, end: float) -> bool:
    return start <= beat < end


def _wall(w: Wall, start: float, end: float, shift: Shift) -> Wall | None:
    if w.duration <= 0:
        return replace(w, beat=shift(w.beat)) if _inside(w.beat, start, end) else None
    a, b = max(w.beat, start), min(w.beat + w.duration, end)
    if b <= a:
        return None
    return replace(w, beat=shift(a), duration=b - a)


def _slider(s: object, start: float, end: float, shift: Shift) -> dict | None:
    """An arc or chain kept whole, or None when its head or tail lies outside the window."""
    try:
        head, tail = float(s["b"]), float(s["tb"])  # type: ignore[index]
    except (KeyError, TypeError, ValueError):
        return None
    if head < start or tail >= end or tail < head:
        return None
    out = dict(s)  # type: ignore[call-overload]
    out["b"], out["tb"] = shift(head), shift(tail)
    return out


def _group(g: object, start: float, end: float, shift: Shift) -> dict | None:
    beat = g.get("b") if isinstance(g, dict) else None
    ok = isinstance(beat, int | float) and not isinstance(beat, bool)
    if not ok or not _inside(beat, start, end):  # type: ignore[arg-type]
        return None
    out = copy.deepcopy(g)
    out["b"] = shift(beat)  # type: ignore[arg-type]
    return out


def _blackouts(groups: list[dict], beat: float) -> list[dict]:
    """A dark copy per group id, taken from the last kept group of that id: first event of each
    box only, at brightness 0, instant transition, no strobe."""
    last: dict[object, dict] = {}
    for g in groups:
        last[g.get("g")] = g
    out = []
    for g in last.values():
        dark = copy.deepcopy(g)
        dark["b"] = beat
        for box in dark.get("e", []):
            events = box.get("e") or []
            if events:
                box["e"] = [dict(events[0], b=0.0, i=0, s=0.0, f=0)]
        out.append(dark)
    return out


def _carried(events: list[BasicEvent], start: float) -> dict[int, BasicEvent]:
    """The last non-off event of each light type before the cut."""
    last: dict[int, BasicEvent] = {}
    for e in sorted(events, key=lambda e: e.beat):
        if e.beat < start and e.type in LIGHT_TYPES:
            last[e.type] = e
    return {t: e for t, e in last.items() if e.value != 0}


def _lights(
    d: Difficulty, start: float, end: float, shift: Shift, lead_beats: float, length_beats: float
) -> tuple[list[BasicEvent], list[tuple[float, bool]]]:
    kept = [
        BasicEvent(shift(e.beat), e.type, e.value, e.float_value)
        for e in d.events
        if _inside(e.beat, start, end)
    ]
    first_kept: dict[int, float] = {}
    for e in kept:
        first_kept[e.type] = min(e.beat, first_kept.get(e.type, math.inf))
    fade = []
    for light, carried in _carried(d.events, start).items():
        for i, level in enumerate(FADE_LEVELS):
            beat = lead_beats + i * FADE_STEP_BEATS
            if beat < first_kept.get(light, math.inf):
                fade.append(BasicEvent(beat, light, carried.value, level))
    off = [BasicEvent(0.0, t, 0) for t in LIGHT_TYPES]
    dark = [BasicEvent(length_beats, t, 0) for t in LIGHT_TYPES]
    boosts = [(shift(b), o) for b, o in d.boosts if _inside(b, start, end)]
    before = [o for b, o in sorted(d.boosts) if b < start]
    if before and before[-1]:
        boosts.append((0.0, True))
    if boosts:
        boosts.append((length_beats, False))
    return sorted(off + fade + kept + dark), sorted(boosts)


def crop_difficulty(
    d: Difficulty, start: float, end: float, lead_beats: float, bpm_events: list[BpmEvent]
) -> Difficulty:
    def shift(beat: float) -> float:
        return beat - start + lead_beats

    length_beats = lead_beats + (end - start)
    walls = [w2 for w in d.walls if (w2 := _wall(w, start, end, shift)) is not None]
    events, boosts = _lights(d, start, end, shift, lead_beats, length_beats)
    raw = dict(d.raw)
    for key in SLIDER_KEYS:
        raw[key] = [
            s2 for s in d.raw.get(key, []) if (s2 := _slider(s, start, end, shift)) is not None
        ]
    for key in BOX_KEYS:
        raw[key] = [
            g2 for g in d.raw.get(key, []) if (g2 := _group(g, start, end, shift)) is not None
        ]
    raw[COLOR_GROUPS] = raw[COLOR_GROUPS] + _blackouts(raw[COLOR_GROUPS], length_beats)
    return Difficulty(
        name=d.name,
        njs=d.njs,
        offset=d.offset,
        notes=[replace(n, beat=shift(n.beat)) for n in d.notes if _inside(n.beat, start, end)],
        bombs=[replace(b, beat=shift(b.beat)) for b in d.bombs if _inside(b.beat, start, end)],
        walls=sorted(walls),
        events=events,
        boosts=boosts,
        bpm_events=list(bpm_events),
        raw=raw,
        filename=d.filename,
    )


def crop_beatmap(beatmap: Beatmap, timing: Timing, start_beat: float, end_beat: float) -> Cropped:
    """Crop every difficulty to [start_beat, end_beat). `timing` is `grid_timing(beatmap)`."""
    events = grid_events(beatmap)
    bpm0 = tempo_at(beatmap.info.bpm, events, start_beat)
    start_s, end_s = timing.to_seconds(start_beat), timing.to_seconds(end_beat)
    offsets = [
        timing.to_seconds(b) - start_s
        for d in beatmap.difficulties.values()
        for b in note_beats(d)
        if _inside(b, start_beat, end_beat)
    ]
    need = max(0.0, LEAD_IN_S - min(offsets)) if offsets else 0.0
    lead_beats = math.ceil(need * bpm0 / 60.0 - 1e-9)
    lead_s = lead_beats * 60.0 / bpm0
    new_events = [
        BpmEvent(e.beat - start_beat + lead_beats, e.bpm)
        for e in sorted(events, key=lambda e: e.beat)
        if start_beat < e.beat < end_beat
    ]
    diffs = {
        name: crop_difficulty(d, start_beat, end_beat, lead_beats, new_events)
        for name, d in beatmap.difficulties.items()
    }
    fade_out_s = end_s - timing.to_seconds(end_beat - BAR)
    cropped = Beatmap(replace(beatmap.info, bpm=bpm0), diffs, "")
    return Cropped(cropped, start_s, end_s - start_s, lead_s, fade_out_s)
