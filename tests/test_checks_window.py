"""Windowed rules: findings of a window equal the whole-difficulty findings that overlap it."""

import random
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.analysis import Analysis
from saber_tooth.checks import LOCAL_REACH_S, REACH_S, RULES, Finding, check_difficulty
from saber_tooth.mapio import load_map
from saber_tooth.model import Bomb, Color, Cut, Difficulty, Note, Wall
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing

MAPS = Path(__file__).parent / "fixtures" / "maps"
T = Timing(120, [])
PROFILE_MAX_REACH_S = 1.5


def busy(seconds=80):
    k = [i * 0.5 for i in range(seconds * 2)]
    return Analysis("x", "C major", 120.0, k, k, [], k, None)


def _ident(f: Finding):
    return (f.rule, f.difficulty, f.beat_start, f.beat_end, f.severity, f.message)


def assert_window_equals_whole(d, timing, profile, analysis, lo, hi):
    whole = check_difficulty(d, timing, profile, analysis)
    want = [f for f in whole if f.beat_start <= hi and f.beat_end >= lo]
    got = check_difficulty(d, timing, profile, analysis, window=(lo, hi))
    assert [_ident(f) for f in got] == [_ident(f) for f in want]


note_st = st.builds(
    lambda i, x, y, c, cut: Note(4 + i * 0.125, x, y, Color(c), Cut(cut)),
    st.integers(0, 400),
    st.integers(0, 3),
    st.integers(0, 2),
    st.integers(0, 1),
    st.integers(0, 8),
)
bomb_st = st.builds(
    lambda i, x, y: Bomb(4 + i * 0.25, x, y),
    st.integers(0, 200),
    st.integers(0, 3),
    st.integers(0, 2),
)
wall_st = st.builds(
    lambda i, x, dur, w: Wall(4 + i * 0.5, x, 0, dur, w, 3),
    st.integers(0, 100),
    st.integers(0, 3),
    st.sampled_from([0.1, 0.4, 1.5, 4.0]),
    st.integers(1, 3),
)


@settings(max_examples=60, deadline=None)
@given(
    st.lists(note_st, min_size=1, max_size=300),
    st.lists(bomb_st, max_size=20),
    st.lists(wall_st, max_size=12),
    st.sampled_from(sorted(PROFILES)),
    st.floats(0, 60),
    st.floats(0, 30),
    st.booleans(),
)
def test_window_equals_whole_restricted_to_the_window(notes, bombs, walls, name, lo, span, music):
    d = Difficulty(name, 16, 0, notes=sorted(notes), bombs=sorted(bombs), walls=sorted(walls))
    assert_window_equals_whole(d, T, PROFILES[name], busy() if music else None, lo, lo + span)


@pytest.mark.parametrize("folder", sorted(p.name for p in MAPS.iterdir() if p.is_dir()))
def test_window_equals_whole_on_fixture_maps(folder):
    bm = load_map(MAPS / folder)
    for name, d in bm.difficulties.items():
        if name not in PROFILES:
            continue
        timing = Timing(bm.info.bpm, d.bpm_events)
        last = d.notes[-1].beat if d.notes else 0.0
        for lo in (0.0, last / 3, last * 2 / 3):
            assert_window_equals_whole(d, timing, PROFILES[name], busy(), lo, lo + last / 4)


def test_window_equals_whole_on_a_large_dense_map():
    rng = random.Random(5)  # noqa: S311  deterministic data
    notes = [
        Note(
            8 + i * 0.1, rng.randint(0, 3), rng.randint(0, 2), Color(i % 2), Cut(rng.randint(0, 8))
        )
        for i in range(2000)
    ]
    d = Difficulty("Expert", 16, 0, notes=notes)
    for lo in (0, 40, 120, 190, 400):
        assert_window_equals_whole(d, T, PROFILES["Expert"], busy(120), lo, lo + 9)


def test_every_rule_declares_its_reach_and_only_empty_gap_is_global():
    assert set(REACH_S) == set(RULES)
    assert [r for r, s in REACH_S.items() if s is None] == ["empty-gap"]
    assert LOCAL_REACH_S > PROFILE_MAX_REACH_S
    limits = [
        v
        for p in PROFILES.values()
        for k, v in vars(p).items()
        if k.endswith("_s") and isinstance(v, int | float)
    ]
    assert max(limits, default=0) <= LOCAL_REACH_S
