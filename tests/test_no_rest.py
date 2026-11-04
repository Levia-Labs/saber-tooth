"""no-rest: sustained dense play without a rest zone; plan inserts rests; fixer opens one."""

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth import fixer as fx
from saber_tooth.checks import check_difficulty, run_checks
from saber_tooth.checks.gaps import REST_BEATS, REST_SPAN_S
from saber_tooth.generator import generate_all
from saber_tooth.generator.candidates import BAR_BEATS, build_candidates, phase_of
from saber_tooth.generator.plan import plan_events
from saber_tooth.model import Color, Cut, Difficulty, Note
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing
from tests.test_fixer import bm
from tests.test_generator import synth

T = Timing(120.0, [])  # one beat is half a second


def stream(beats, name="Expert"):
    notes = [Note(b, i % 2, 0, Color(i % 2), Cut.DOWN) for i, b in enumerate(beats)]
    return Difficulty(name, PROFILES[name].njs, 0, notes=notes)


def flagged(d, name="Expert"):
    found = check_difficulty(d, T, PROFILES[name], rules={"no-rest"})
    return [f for f in found if f.rule == "no-rest"]


def dense(seconds):
    return [float(i) for i in range(int(seconds / 0.5))]  # a note every beat


def test_long_dense_play_is_flagged():
    d = stream(dense(REST_SPAN_S["Expert"] + 20))
    assert len(flagged(d)) == 1


def test_rest_zone_in_the_middle_clears_the_flag():
    beats = dense(REST_SPAN_S["Expert"] + 20)
    mid = len(beats) // 2
    assert flagged(stream(beats)) != []
    assert flagged(stream(beats[:mid] + beats[mid + 10 :])) == []  # ten beats of silence


def test_short_dense_play_is_fine():
    assert flagged(stream(dense(REST_SPAN_S["Expert"] - 5))) == []


@settings(max_examples=60, deadline=None)
@given(st.lists(st.floats(0.0, 400.0), min_size=0, max_size=300))
def test_flagged_spans_hold_no_rest_window(raw):
    beats = sorted(round(b * 4) / 4 for b in raw)
    d = stream(beats)
    for f in flagged(d):
        assert T.to_seconds(f.beat_end) - T.to_seconds(f.beat_start) >= REST_SPAN_S["Expert"]
        inside = [b for b in beats if f.beat_start <= b <= f.beat_end]
        assert all(inside[i + 3] - inside[i] < REST_BEATS for i in range(len(inside) - 3))


def _plan(bpm, seconds, name, swing=0.0):
    a = synth(bpm, seconds, swing)
    timing = Timing(bpm, [])
    profile = PROFILES[name]
    cands, bars = build_candidates(a, timing, profile, phase_of(a, timing))
    return plan_events(cands, bars, timing, profile, {h: float("-inf") for h in Color}), bars


@settings(max_examples=12, deadline=None)
@given(st.sampled_from(["Hard", "Expert", "ExpertPlus"]), st.floats(80, 190), st.integers(120, 240))
def test_plan_inserts_quiet_rest_zones(name, bpm, seconds):
    plan, bars = _plan(bpm, seconds, name)
    assert plan.rests, "a long dense map needs a rest zone"
    for lo, hi in plan.rests:
        assert 2 <= hi - lo <= 4
        counts = [
            sum(len(e.hands) for e in plan.events if int(e.rel // BAR_BEATS) == b)
            for b in range(lo, hi)
        ]
        assert max(counts) <= 1
        assert min(bars.energy[b] for b in range(lo, hi)) <= max(bars.energy.values())


@settings(max_examples=10, deadline=None)
@given(st.floats(80, 190), st.integers(100, 200), st.integers(0, 50))
def test_generated_maps_never_lack_rest(bpm, seconds, seed):
    a = synth(bpm, seconds, 0.1)
    timing, diffs = generate_all(a, seed)
    for name, d in diffs.items():
        assert [
            f for f in check_difficulty(d, timing, PROFILES[name], a) if f.rule == "no-rest"
        ] == []


def test_fixer_opens_a_rest_zone():
    m = bm(stream(dense(REST_SPAN_S["Expert"] + 20)).notes)
    f = next(f for f in run_checks(m, difficulty="Expert") if f.rule == "no-rest")
    p = fx.propose(m, f, None, None, 1)
    assert p is not None
    fixed = fx.apply_ops(m, p.ops)
    assert "no-rest" not in {g.rule for g in run_checks(fixed, difficulty="Expert")}
