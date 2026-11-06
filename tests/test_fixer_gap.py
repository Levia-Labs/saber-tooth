"""empty-gap fix: a busy 10-beat gap on Easy next to dot swings still gets a verified fill."""

import itertools

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth import fixer as fx
from saber_tooth.checks import run_checks
from saber_tooth.checks.constants import PARITY_DOT
from saber_tooth.fixer import gap_fill
from saber_tooth.model import CUT_VECTORS, Color, Cut, Note
from tests.test_fixer import bm, busy, left_ids


def easy_map(entry_cut: Cut, exit_cut: Cut):
    ns = []
    for i in range(15):
        ns.append(Note(8.0 + 2 * i, 1 + i % 2, 1, Color(i % 2), Cut.DOWN if i % 2 == 0 else Cut.UP))
    ns += [Note(37.0, 1, 1, Color.RED, entry_cut), Note(38.0, 2, 1, Color.BLUE, entry_cut)]
    ns += [Note(48.0, 1, 1, Color.RED, Cut.ANY), Note(49.0, 1, 1, Color.RED, exit_cut)]
    ns += [Note(50.0, 2, 1, Color.BLUE, exit_cut)]
    for j in range(12):
        ns.append(Note(54 + 2 * j, 1 + j % 2, 1, Color(j % 2), Cut.DOWN if j % 2 == 0 else Cut.UP))
    return bm(ns, "Easy")


@pytest.mark.parametrize(
    ("entry", "exit_"),
    [(Cut.UP, Cut.LEFT), (Cut.DOWN, Cut.RIGHT), (Cut.LEFT, Cut.UP), (Cut.UP_LEFT, Cut.LEFT)],
)
def test_busy_ten_beat_gap_before_dot_swing_gets_verified_fill(entry, exit_):
    m, a = easy_map(entry, exit_), busy(60)
    f = next(
        g
        for g in run_checks(m, a, difficulty="Easy")
        if g.rule == "empty-gap" and 36 < g.beat_start < 40
    )
    out = fx.propose_with_reason(m, f, a, None, 1)
    assert out.proposal is not None, out.reason
    fixed = fx.apply_ops(m, out.proposal.ops)
    assert (f.rule, f.beat_start, f.beat_end) not in left_ids(fixed, "Easy", a)


GRID = st.sampled_from([0.25, 0.5, 1.0])


@settings(max_examples=200, deadline=None)
@given(
    GRID,
    st.floats(0, 200),
    st.floats(8, 60),
    st.integers(1, 12),
    st.floats(0.25, 3),
    st.lists(st.floats(0, 260), max_size=40),
)
def test_fill_slots_inside_window_on_grid_and_spaced(grid, start, length, count, spacing, ons):
    end = start + length
    slots = gap_fill.fill_slots(start, end, grid, spacing, count, sorted(ons))
    if slots is None:
        return
    assert len(slots) == count
    assert all(start < b < end for b in slots)
    assert all(abs(b / grid - round(b / grid)) < 1e-9 for b in slots)
    assert all(b2 - b1 >= spacing - 1e-9 for b1, b2 in itertools.pairwise(slots))


vec_st = st.one_of(
    st.none(), st.sampled_from([c for c in Cut if c != Cut.ANY]).map(CUT_VECTORS.get)
)


@settings(max_examples=200, deadline=None)
@given(
    st.lists(st.integers(1, 60), min_size=1, max_size=12, unique=True).map(sorted),
    st.sampled_from(list(Color)),
    vec_st,
    vec_st,
)
def test_fill_notes_alternate_per_hand_and_stay_in_bounds(beats, first, red_entry, blue_entry):
    entry = {Color.RED: red_entry, Color.BLUE: blue_entry}
    notes = gap_fill.fill_notes([float(b) for b in beats], first, entry)
    assert [n.beat for n in notes] == [float(b) for b in beats]
    for n in notes:
        assert 0 <= n.x <= 3 and 0 <= n.y <= 2 and n.cut != Cut.ANY
        assert (n.x <= 1) == (n.color == Color.RED)
    for hand in Color:
        vs = [CUT_VECTORS[n.cut] for n in notes if n.color == hand]
        if entry[hand] is not None and vs:
            vs.insert(0, entry[hand])
        for a, b in itertools.pairwise(vs):
            assert a[0] * b[0] + a[1] * b[1] <= PARITY_DOT
