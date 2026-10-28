"""Song sections: where the music changes, found from the map and, when analysed, the audio."""

import math
from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise

from saber_tooth.analysis import Analysis, onset_density
from saber_tooth.crop.nps import mean_nps, note_beats, peak
from saber_tooth.crop.phrases import EPS, PHRASE_BEATS, Grid, hardest
from saber_tooth.lightshow.units import BAR
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import Beatmap, Difficulty
from saber_tooth.timing import Timing

PERCENTILE = 0.70
MIN_SECTION_BEATS = PHRASE_BEATS  # a section is at least 8 bars


@dataclass(frozen=True)
class Section:
    start_beat: float
    end_beat: float
    nps: float
    intensity: float


@dataclass(frozen=True)
class SectionMap:
    boundaries: list[float]
    sections: list[Section]
    map_only: bool


def _count(times: list[float], lo: float, hi: float) -> int:
    return bisect_left(times, hi) - bisect_left(times, lo)


def _in(beat: object, lo: float, hi: float) -> bool:
    return isinstance(beat, int | float) and not isinstance(beat, bool) and lo <= beat < hi


def light_count(d: Difficulty, lo: float, hi: float) -> int:
    """Basic events, boost events and event box groups that start in [lo, hi)."""
    n = sum(1 for e in d.events if lo <= e.beat < hi) + sum(1 for b, _ in d.boosts if lo <= b < hi)
    for key in BOX_KEYS:
        n += sum(1 for g in d.raw.get(key, []) if isinstance(g, dict) and _in(g.get("b"), lo, hi))
    return n


def _pitch_range(a: Analysis, lo_s: float, hi_s: float) -> float:
    ids = a.melody_ids[bisect_left(a.melody, lo_s) : bisect_left(a.melody, hi_s)]
    return float(max(ids) - min(ids)) if len(ids) > 1 else 0.0


def make_features(
    beatmap: Beatmap, timing: Timing, analysis: Analysis | None
) -> Callable[[float, float], list[float]]:
    diffs = list(beatmap.difficulties.values())
    heads = note_beats(hardest(beatmap))

    def features(lo: float, hi: float) -> list[float]:
        bars = (hi - lo) / BAR
        out = [max(light_count(d, lo, hi) for d in diffs) / bars, _count(heads, lo, hi) / bars]
        if analysis is not None:
            a, b = timing.to_seconds(lo), timing.to_seconds(hi)
            secs = b - a
            out += [
                onset_density(analysis, a, b),
                (_count(analysis.bass, a, b) + _count(analysis.chords, a, b)) / secs,
                _count(analysis.melody, a, b) / secs,
                _pitch_range(analysis, a, b),
            ]
        return out

    return features


def change_scores(
    grid: Grid, features: Callable[[float, float], list[float]]
) -> list[tuple[float, float]]:
    """(beat, score) per phrase start with a full phrase on each side: the sum over terms of the
    jump between the 8 bars before and the 8 bars after, each term divided by its song maximum."""
    jumps: list[tuple[float, list[float]]] = []
    beat = grid.anchor + PHRASE_BEATS
    while beat + PHRASE_BEATS <= grid.end_beat + EPS:
        before = features(beat - PHRASE_BEATS, beat)
        after = features(beat, beat + PHRASE_BEATS)
        jumps.append((beat, [abs(x - y) for x, y in zip(after, before, strict=True)]))
        beat += PHRASE_BEATS
    if not jumps:
        return []
    peaks = [max(j[i] for _, j in jumps) for i in range(len(jumps[0][1]))]
    return [
        (b, sum(v / p if p > 0 else 0.0 for v, p in zip(j, peaks, strict=True))) for b, j in jumps
    ]


def _percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def pick_boundaries(grid: Grid, scored: list[tuple[float, float]]) -> list[float]:
    """The grid anchor, every score above the 70th percentile, and the last bar line. Boundaries
    closer than 8 bars keep the higher score; the anchor and the last bar line always win."""
    bars = grid.bars
    if len(bars) < 2:
        return bars[:1]
    threshold = _percentile([s for _, s in scored], PERCENTILE) if scored else 0.0
    picks = [(grid.anchor, math.inf)]
    picks += [(b, s) for b, s in scored if s > threshold]
    picks.append((bars[-1], math.inf))
    kept: list[tuple[float, float]] = []
    for beat, score in picks:
        if kept and beat - kept[-1][0] < MIN_SECTION_BEATS - EPS:
            if score > kept[-1][1]:
                kept[-1] = (beat, score)
            continue
        kept.append((beat, score))
    return [b for b, _ in kept]


def find_sections(
    beatmap: Beatmap,
    grid: Grid,
    timing: Timing,
    analysis: Analysis | None,
    series: list[float],
) -> SectionMap:
    """Sections between boundaries, each with its mean NPS and intensity against the song peak."""
    scored = change_scores(grid, make_features(beatmap, timing, analysis))
    bounds = pick_boundaries(grid, scored)
    top = peak(series)
    sections = []
    for a, b in pairwise(bounds):
        nps = mean_nps(series, timing.to_seconds(a), timing.to_seconds(b))
        sections.append(Section(a, b, nps, nps / top if top > 0 else 0.0))
    return SectionMap(bounds, sections, analysis is None)
