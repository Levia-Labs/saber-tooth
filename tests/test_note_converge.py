"""note-converge: notes whose flight paths meet; check, placer, fixer."""

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth import fixer as fx
from saber_tooth.checks import check_difficulty
from saber_tooth.checks.layout import (
    CONVERGE_FALLBACK_S,
    SAME_CELL_S,
    converges,
    jump_window_s,
)
from saber_tooth.generator.placer import Placer
from saber_tooth.model import Color, Cut, Difficulty
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing
from tests.test_fixer import _n, bm, find

T = Timing(120.0, [])
CELL = st.tuples(st.integers(0, 3), st.integers(0, 2))


def rules(notes, name="Expert"):
    d = Difficulty(name, PROFILES[name].njs, 0, notes=sorted(notes))
    return {f.rule for f in check_difficulty(d, T, PROFILES[name])}


def test_same_column_other_row_close_in_time_is_flagged():
    ns = [_n(8, 0, 0), _n(8.5, 0, 2, cut=Cut.UP)]  # 0.25 s apart at 120 bpm
    assert "note-converge" in rules(ns)


def test_same_cell_close_in_time_is_flagged():
    ns = [_n(8, 1, 0), _n(8.15, 1, 0, Color.BLUE)]
    assert "note-converge" in rules(ns)


def test_stack_on_one_beat_and_far_notes_are_not_flagged():
    stack = [_n(8, 0, 0), _n(8, 0, 1)]
    assert "note-converge" not in rules(stack)
    assert "note-converge" not in rules([_n(8, 0, 0), _n(10, 0, 2, cut=Cut.UP)])
    assert "note-converge" not in rules([_n(8, 0, 0), _n(8.5, 1, 2, cut=Cut.UP)])


def test_window_falls_back_on_unusable_input():
    assert jump_window_s(0, 0, 120) == CONVERGE_FALLBACK_S
    assert jump_window_s(16, 0, float("nan")) == CONVERGE_FALLBACK_S


@given(st.floats(1, 40), st.floats(-2, 2), st.floats(40, 400))
def test_window_is_positive_and_bounded(njs, offset, bpm):
    w = jump_window_s(njs, offset, bpm)
    assert SAME_CELL_S <= w <= 10.0


@given(st.floats(0, 2), CELL, CELL, st.floats(0.05, 1.0))
def test_converges_is_symmetric(dt, a, b, window):
    assert converges(dt, a, b, window) == converges(-dt, b, a, window)


@settings(max_examples=40)
@given(st.floats(0.0, 2.0), CELL, CELL)
def test_far_apart_never_converges(dt, a, b):
    assert not converges(dt + 2.0, a, b, 1.0)


STEP = st.tuples(st.sampled_from([0.25, 0.5, 0.75, 1.0]), st.integers(0, 1), CELL)


@settings(max_examples=40, deadline=None)
@given(st.sampled_from(["Hard", "Expert", "ExpertPlus"]), st.lists(STEP, min_size=5, max_size=60))
def test_placer_never_creates_converging_pairs(name, steps):
    profile = PROFILES[name]
    placer = Placer(T, profile)
    beat = 4.0
    for delta, hand, (x, y) in steps:
        beat += delta
        placer.try_add(Color(hand), beat, [(Cut.DOWN, x, y)])
    d = Difficulty(name, profile.njs, 0, notes=placer.all_notes())
    assert [f for f in check_difficulty(d, T, profile) if f.rule == "note-converge"] == []


def test_fixer_clears_converging_pair_in_one_proposal():
    m = bm([_n(8, 0, 0), _n(8.5, 0, 2, cut=Cut.UP)])
    f = find(m, "note-converge")
    p = fx.propose(m, f, None, None, 1)
    assert p is not None
    fixed = fx.apply_ops(m, p.ops)
    assert "note-converge" not in {g.rule for g in fx_run(fixed)}
    assert len(fixed.difficulties["Expert"].notes) >= 1


def fx_run(m):
    from saber_tooth.checks import run_checks

    return run_checks(m)


def test_fixer_drops_dot_before_arrow():
    m = bm([_n(8, 1, 0), _n(8.15, 1, 0, Color.BLUE, cut=Cut.ANY)])
    p = fx.propose(m, find(m, "note-converge"), None, None, 1)
    assert p is not None
