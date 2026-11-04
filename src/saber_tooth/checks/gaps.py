from bisect import bisect_left, bisect_right
from itertools import pairwise

from saber_tooth.analysis import onset_density
from saber_tooth.checks.constants import MIN_GAP_DENSITY
from saber_tooth.checks.finding import Finding

REST_BEATS = 8.0  # a rest zone: this many beats (two bars) ...
REST_MAX_NOTES = 2  # ... holding at most this many notes (0-1 per bar)
# Longest stretch of play in seconds before a rest zone is due, easier tiers may play longer.
REST_SPAN_S = {"Easy": 90.0, "Normal": 70.0, "Hard": 50.0, "Expert": 40.0, "ExpertPlus": 30.0}
DEFAULT_REST_SPAN_S = 30.0
EPS = 1e-6


def _beat(n) -> float:
    return n.beat


def _gap_edges(d, timing, analysis, window=None) -> list[tuple[float, float]]:
    """Gaps between consecutive note beats and at both ends of the analysed range; with a
    (lo, hi) beat window only the gaps that can overlap it (notes are sorted by beat)."""
    notes, first, last = d.notes, 0, len(d.notes)
    if window is not None and notes:
        first = max(bisect_left(notes, window[0], key=_beat) - 1, 0)
        last = min(bisect_right(notes, window[1], key=_beat) + 1, len(notes))
    beats = sorted({n.beat for n in notes[first:last]})
    onsets = analysis.beats + analysis.kick + analysis.snare + analysis.hh
    if not beats:  # no notes at all: one gap over the whole analysed range
        if not onsets:
            return []
        return [(timing.to_beats(min(onsets)), timing.to_beats(max(onsets)))]
    edges = []
    if analysis.beats and first == 0:
        edges.append((timing.to_beats(analysis.beats[0]), beats[0]))
    edges.extend(pairwise(beats))
    if onsets and last == len(notes):
        edges.append((beats[-1], timing.to_beats(max(onsets))))
    return edges


def empty_gap(d, swings, timing, profile, analysis, window=None) -> list[Finding]:
    if analysis is None:
        return []
    out = []
    for start, end in _gap_edges(d, timing, analysis, window):
        if end - start < profile.gap_beats:
            continue
        density = onset_density(analysis, timing.to_seconds(start), timing.to_seconds(end))
        if density >= MIN_GAP_DENSITY:
            msg = f"no notes for {end - start:.1f} beats while the music is busy"
            out.append(Finding("empty-gap", d.name, start, end, "warn", msg))
    return out


def rest_zones(beats: list[float]) -> list[tuple[float, float]]:
    """Beat ranges that hold at most REST_MAX_NOTES notes over at least REST_BEATS, from the
    note before to the note after; `beats` is sorted. The play before the first note is no rest."""
    n, k = len(beats), REST_MAX_NOTES
    zones = []
    for i in range(-1, n - k - 1):
        lo = beats[i] if i >= 0 else beats[0]
        hi = beats[i + k + 1] if i + k + 1 < n else beats[-1]
        if hi - lo >= REST_BEATS - EPS:
            zones.append((lo, hi))
    return zones


def no_rest(d, swings, timing, profile, analysis=None, window=None) -> list[Finding]:
    if not d.notes:
        return []
    beats = sorted(n.beat for n in d.notes)
    span = REST_SPAN_S.get(profile.name, DEFAULT_REST_SPAN_S)
    out, cursor = [], beats[0]
    stretches = []
    for lo, hi in [*rest_zones(beats), (beats[-1], beats[-1])]:
        stretches.append((cursor, lo))
        cursor = max(cursor, hi)
    for start, end in stretches:
        if timing.to_seconds(end) - timing.to_seconds(start) >= span:
            msg = f"no rest for {end - start:.0f} beats of dense play"
            out.append(Finding("no-rest", d.name, start, end, "warn", msg))
    return out
