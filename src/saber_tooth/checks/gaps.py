from itertools import pairwise

from saber_tooth.analysis import onset_density
from saber_tooth.checks.finding import Finding

MIN_DENSITY = 1.5


def _gap_edges(d, timing, analysis) -> list[tuple[float, float]]:
    beats = sorted({n.beat for n in d.notes})
    if not beats:
        return []
    onsets = analysis.beats + analysis.kick + analysis.snare + analysis.hh
    edges = []
    if analysis.beats:
        edges.append((timing.to_beats(analysis.beats[0]), beats[0]))
    edges.extend(pairwise(beats))
    if onsets:
        edges.append((beats[-1], timing.to_beats(max(onsets))))
    return edges


def empty_gap(d, swings, timing, profile, analysis) -> list[Finding]:
    if analysis is None:
        return []
    out = []
    for start, end in _gap_edges(d, timing, analysis):
        if end - start < profile.gap_beats:
            continue
        density = onset_density(analysis, timing.to_seconds(start), timing.to_seconds(end))
        if density >= MIN_DENSITY:
            msg = f"no notes for {end - start:.1f} beats while the music is busy"
            out.append(Finding("empty-gap", d.name, start, end, "warn", msg))
    return out
