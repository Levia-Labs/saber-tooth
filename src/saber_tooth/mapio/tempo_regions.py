"""Convert v4 audio-data `bpmData` and legacy `BPMInfo.dat` `_regions` to tempo events."""

import math

from saber_tooth.mapio.errors import MapParseError
from saber_tooth.model import BpmEvent

SAME_BPM = 1e-4  # consecutive tempos closer than this relative amount are one tempo
TOL = 1e-6  # overlap tolerance
GAP_SAMPLES = 2  # a sample gap this small with no beat gap is rounding in the source
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


def _segments(spans: list[tuple[float, float, float, float]]) -> list[tuple[float, ...]]:
    """Join spans (si, ei, sb, eb) into one gapless sample-to-beat piecewise-linear map."""
    spans = sorted(spans)
    first = spans[0]
    out: list[tuple[float, ...]] = []
    if first[0] > 0 and first[2] <= TOL:
        raise MapParseError("audio lead-in before beat 0 is not supported")
    if first[0] > 0:
        out.append((0.0, first[0], 0.0, first[2]))
    elif first[2] > TOL:
        raise MapParseError("unsupported tempo layout: beat offset at sample 0")
    pei, peb = 0.0, 0.0
    for span in spans:
        si, _, sb, _ = span
        if si < pei - TOL or sb < peb - TOL:
            raise MapParseError("unsupported tempo layout: overlapping regions")
        dsi, dsb = si - pei, sb - peb
        if out and dsb <= TOL and dsi <= GAP_SAMPLES:
            pass
        elif out and (dsi > TOL or dsb > TOL):
            if dsi <= TOL or dsb <= TOL:
                raise MapParseError("unsupported tempo layout: gap with a stalled axis")
            out.append((pei, si, peb, sb))
        out.append(span)
        pei, peb = span[1], span[3]
    return out


def regions_to_events(data: dict, keys: tuple[str, ...]) -> list[BpmEvent]:
    """Return tempo events (one per segment) for a parsed audio-data or BPMInfo object."""
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
        if ei < si or eb < sb or sb < 0 or si < 0:
            raise MapParseError("bad tempo region: reversed or negative range")
        if ei == si and eb == sb:
            continue
        if ei == si or eb == sb:
            raise MapParseError("unsupported tempo layout: region with one empty axis")
        spans.append((si, ei, sb, eb))
    if not spans:
        return []
    events = []
    for si, ei, sb, eb in _segments(spans):
        bpm = (eb - sb) / ((ei - si) / freq) * 60.0
        if not math.isfinite(bpm) or bpm <= 0:
            raise MapParseError("bad tempo region: tempo out of range")
        events.append(BpmEvent(sb, bpm))
    return events


def merge_events(own: list[BpmEvent], extra: list[BpmEvent], initial_bpm: float) -> list[BpmEvent]:
    """Combine own and region events (own win at a shared beat), then drop repeated tempos."""
    beats = {e.beat for e in own}
    merged = sorted([*own, *(e for e in extra if e.beat not in beats)], key=lambda e: e.beat)
    out: list[BpmEvent] = []
    prev = initial_bpm
    for e in merged:
        if abs(e.bpm - prev) < prev * SAME_BPM:
            continue
        out.append(e)
        prev = e.bpm
    return out
