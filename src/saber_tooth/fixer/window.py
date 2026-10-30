"""Time windows: batches of one difficulty, and verification of a fix against its window only.

Every rule looks at most MARGIN_S seconds across notes (the largest reset, crossing, vision
and dodge limits in the profiles are 1.5 s), so a change is fully judged by the findings in
its span plus that margin. The checked slice is twice the margin wide, which keeps the
artefacts a cut makes at the slice edge outside the compared span.
"""

from bisect import bisect_right

from saber_tooth.analysis import Analysis
from saber_tooth.checks import Finding, check_difficulty
from saber_tooth.checks.slicing import slice_difficulty
from saber_tooth.fixer.fill_op import Fill
from saber_tooth.fixer.ops import Delete, DeleteWall, Flip, Move, Op, Recolor
from saber_tooth.model import Cut, Difficulty
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing

BATCH_NOTES = 120  # ~0.5 s of a dense Expert+ run per rule pass; 20-40 batches on a long map
MARGIN_S = 2.0  # above every profile limit (max 1.5 s) so no rule reaches past it
WINDOW_MIN_NOTES = 300  # below this a whole-difficulty check is as cheap as a window
_LOCAL = (Move, Recolor, Flip, Delete, DeleteWall, Fill)


def batch_edges(d: Difficulty, size: int | None = None) -> list[float]:
    """Start beats of the batches after the first: a cut every `size` notes, on a new beat."""
    size = size or BATCH_NOTES
    beats = sorted({n.beat for n in d.notes})
    per: dict[float, int] = {}
    for n in d.notes:
        per[n.beat] = per.get(n.beat, 0) + 1
    edges, count = [], 0
    for b in beats:
        if count >= size:
            edges.append(b)
            count = 0
        count += per[b]
    return edges


def batch_of(edges: list[float], beat: float) -> int:
    return bisect_right(edges, beat + 1e-9)


def batch_count(d: Difficulty, size: int | None = None) -> int:
    return len(batch_edges(d, size)) + 1


def op_span(ops: list[Op]) -> tuple[str, float, float] | None:
    """(difficulty, first beat, last beat) of ops confined to one difficulty's notes and walls."""
    name, lo, hi = None, float("inf"), float("-inf")
    for op in ops:
        if not isinstance(op, _LOCAL) or name not in (None, op.difficulty):
            return None
        name = op.difficulty
        if isinstance(op, Fill):
            beats = [op.beat_start, op.beat_end] + [n.beat for n in op.notes]
            for w in op.walls_added + op.walls_removed:
                beats += [w.beat, w.beat + w.duration]
        elif isinstance(op, DeleteWall):
            beats = [op.wall.beat, op.wall.beat + op.wall.duration]
        else:
            beats = [op.note.beat]
        lo, hi = min(lo, *beats), max(hi, *beats)
    return None if name is None else (name, lo, hi)


def dot_reach(d: Difficulty, hi: float) -> float:
    """Beat up to which a change at `hi` still moves findings: a dot inherits its hand's last
    directional swing, so a run of dots after `hi` is judged by what the change left behind."""
    reach = hi
    start = bisect_right(d.notes, hi + 1e-9, key=_beat)
    for hand in (0, 1):
        later = (n for n in d.notes[start:] if int(n.color) == hand)
        first = next(later, None)
        if first is None or first.cut != Cut.ANY:
            continue
        last = first.beat
        for n in later:
            last = n.beat
            if n.cut != Cut.ANY:
                break
        reach = max(reach, last)
    return reach


def _beat(n) -> float:
    return n.beat


def window_findings(
    beatmap, name: str, lo: float, hi: float, analysis: Analysis | None
) -> list[Finding]:
    """Findings of one difficulty that touch [lo, hi] widened by the margin."""
    d, profile = beatmap.difficulties.get(name), PROFILES.get(name)
    if d is None or profile is None:
        return []
    timing = Timing(beatmap.info.bpm, d.bpm_events)
    m = timing.to_beats(MARGIN_S) - timing.to_beats(0.0)
    return check_difficulty(d, timing, profile, analysis, window=(lo - m, hi + m))


def swings_near(d: Difficulty, timing: Timing, lo: float, hi: float) -> dict:
    """Swings of the notes around [lo, hi], exact except within a margin of the slice edge."""
    m = timing.to_beats(MARGIN_S) - timing.to_beats(0.0)
    return build_swings(slice_difficulty(d, lo - m, hi + m).notes, timing)
