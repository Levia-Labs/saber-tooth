from bisect import bisect_left, bisect_right
from itertools import pairwise

from saber_tooth.analysis import onset_density
from saber_tooth.checks.constants import MIN_GAP_DENSITY
from saber_tooth.checks.finding import Finding


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
