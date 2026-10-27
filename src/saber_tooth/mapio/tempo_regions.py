"""Convert v4 audio-data `bpmData` and legacy `BPMInfo.dat` `_regions` to tempo events."""

import math

from saber_tooth.mapio.errors import MapParseError
from saber_tooth.model import BpmEvent

SAME_BPM = 1e-4  # consecutive tempos closer than this relative amount are one tempo
V4_KEYS = ("songFrequency", "bpmData", "si", "ei", "sb", "eb")
V2_KEYS = (
    "_songFrequency",
    "_regions",
    "_startSampleIndex",
    "_endSampleIndex",
    "_startBeat",
    "_endBeat",
)


def _num(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise MapParseError(f"bad tempo region number: {value!r}")
    return float(value)


def regions_to_events(data: dict, keys: tuple[str, ...], initial_bpm: float) -> list[BpmEvent]:
    """Return tempo events for a parsed audio-data or BPMInfo object."""
    freq_key, list_key, si_key, ei_key, sb_key, eb_key = keys
    freq = _num(data.get(freq_key))
    regions = data.get(list_key)
    if freq <= 0 or not isinstance(regions, list):
        raise MapParseError("bad tempo regions: frequency or region list invalid")
    spans = []
    for r in regions:
        if not isinstance(r, dict):
            raise MapParseError("bad tempo region: not an object")
        si, ei, sb, eb = (_num(r.get(k)) for k in (si_key, ei_key, sb_key, eb_key))
        if ei < si or eb < sb or sb < 0:
            raise MapParseError("bad tempo region: reversed or negative range")
        if ei > si and eb > sb:
            spans.append((sb, (eb - sb) / ((ei - si) / freq) * 60.0))
    events: list[BpmEvent] = []
    prev = initial_bpm
    for beat, bpm in sorted(spans):
        if abs(bpm - prev) < prev * SAME_BPM:
            continue
        events.append(BpmEvent(beat, bpm))
        prev = bpm
    return events


def merge_events(own: list[BpmEvent], extra: list[BpmEvent]) -> list[BpmEvent]:
    """Combine difficulty-level events with region events; own events win at a shared beat."""
    beats = {e.beat for e in own}
    return sorted([*own, *(e for e in extra if e.beat not in beats)], key=lambda e: e.beat)
