"""Speed-ups of the layout rules and swing grouping keep every finding they had."""

from bisect import bisect_left, bisect_right

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.checks.constants import VISION_MIN_DT
from saber_tooth.checks.finding import Finding
from saber_tooth.checks.layout import (
    SAME_CELL_S,
    converges,
    crossover,
    jump_window_s,
    note_converge,
)
from saber_tooth.model import Color, Cut, Difficulty, Note
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing

T = Timing(120, [])
PROFILE = PROFILES["Expert"]

notes_st = st.lists(
    st.builds(
        lambda i, x, y, c, cut, a: Note(i * 0.0625, x, y, Color(c), Cut(cut), a),
        st.integers(0, 120),
        st.integers(0, 3),
        st.integers(0, 2),
        st.integers(0, 1),
        st.integers(0, 8),
        st.sampled_from([0, 0, 45]),
    ),
    max_size=120,
)


def _old_converge(d: Difficulty, timing: Timing):
    window = jump_window_s(d.njs, d.offset, timing.initial_bpm)
    reach = max(window, SAME_CELL_S)
    out = []
    notes = sorted(d.notes)
    secs = [timing.to_seconds(n.beat) for n in notes]
    for i, n in enumerate(notes):
        for j in range(i + 1, len(notes)):
            m, dt = notes[j], secs[j] - secs[i]
            if dt > reach:
                break
            if converges(dt, (n.x, n.y), (m.x, m.y), window):
                msg = "notes fly into the same spot while jumping to their rows"
                out.append(Finding("note-converge", d.name, n.beat, m.beat, "warn", msg, (n, m)))
    return out


def _old_crossover(d: Difficulty, timing: Timing, profile):
    notes = sorted(d.notes)
    reds = [n for n in notes if n.color == Color.RED]
    blues = [n for n in notes if n.color == Color.BLUE]
    secs = [timing.to_seconds(n.beat) for n in blues]
    window = profile.warn.cross_window_s
    best: dict[Note, tuple[float, Finding]] = {}
    for r in reds:
        rs = timing.to_seconds(r.beat)
        lo, hi = bisect_left(secs, rs - window), bisect_right(secs, rs + window)
        for b, bs in zip(blues[lo:hi], secs[lo:hi], strict=True):
            same = abs(r.beat - b.beat) < 1e-6
            far = r.x - b.x >= 2 and r.x >= 2 and b.x <= 1
            if not (far or (same and r.x > b.x and r.y == b.y)):
                continue
            dt = abs(rs - bs)
            sev = "error" if dt < profile.error.cross_window_s else "warn"
            start, end = min(r.beat, b.beat), max(r.beat, b.beat)
            later = r if (r.beat, 0) > (b.beat, 1) else b
            f = Finding("crossover", d.name, start, end, sev, "hands cross over", (r, b))
            if later not in best or dt < best[later][0]:
                best[later] = (dt, f)
    return [f for _, f in best.values()]


@settings(max_examples=150, deadline=None)
@given(notes_st, st.sampled_from([8.0, 16.0, 22.0]))
def test_converge_and_crossover_match_the_reference(notes, njs):
    d = Difficulty("Expert", njs, 0, notes=list(notes))
    assert VISION_MIN_DT > 0
    assert note_converge(d, None, T, PROFILE) == _old_converge(d, T)
    assert crossover(d, None, T, PROFILE) == _old_crossover(d, T, PROFILE)


@settings(max_examples=100, deadline=None)
@given(notes_st)
def test_swings_do_not_depend_on_input_order(notes):
    shuffled = list(reversed(notes))
    a, b = build_swings(notes, T), build_swings(shuffled, T)
    assert a == b
