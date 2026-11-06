"""A dot inherits the opposite of the swing before it, so a fill that ends before a boundary dot
decides the dot's vector; the swing after the dot must still alternate from it."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.checks import check_difficulty
from saber_tooth.generator import generate_all, generate_difficulty
from saber_tooth.model import DIFFICULTIES, Color, Cut, Difficulty, Note
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import build_swings
from tests.test_generator import realistic, synth

DIRECTIONAL = [c for c in Cut if c != Cut.ANY]


def _dot_exit_case(a, timing, profile, seed, last_cut, lo=20.0, hi=30.0):
    """The original map ends the window on `last_cut`, then a dot, then a swing that alternates
    from the dot's vector. The fill replaces the window; the dot must keep its vector."""
    b_lo, b_hi = timing.to_beats(lo), timing.to_beats(hi)
    before = [Note(b_lo - 2, 1 if h == Color.RED else 2, 1, h, Cut.UP) for h in Color]
    old = [Note(b_hi - 1, 1 if h == Color.RED else 2, 1, h, last_cut) for h in Color]
    after = []
    for h in Color:
        x = 1 if h == Color.RED else 2
        after += [Note(b_hi + 1, x, 0, h, Cut.ANY), Note(b_hi + 2, x, 0, h, last_cut)]
    entry = {h: sw[-1] for h, sw in build_swings(before, timing).items() if sw}
    whole = build_swings(sorted(before + old + after), timing)
    exit_ = {h: next(s for s in sw if s.beat >= b_hi) for h, sw in whole.items()}
    fill = generate_difficulty(a, timing, profile, seed, window=(lo, hi), entry=entry, exit=exit_)
    notes = sorted(before + fill.notes + after)
    merged = Difficulty(profile.name, profile.njs, profile.offset, notes=notes)
    found = check_difficulty(merged, timing, profile, a)
    return [f for f in found if f.rule == "parity-break"]


@pytest.mark.parametrize("last_cut", DIRECTIONAL)
def test_window_exit_dot_keeps_parity(last_cut):
    a = realistic(140, 60)
    timing, _ = generate_all(a, 0)
    for name in DIFFICULTIES:
        for seed in range(6):
            found = _dot_exit_case(a, timing, PROFILES[name], seed, last_cut)
            assert found == [], (name, seed, found[:2])


@settings(max_examples=15, deadline=None)
@given(st.floats(70, 200), st.floats(0, 0.3), st.integers(0, 1000), st.sampled_from(DIRECTIONAL))
def test_no_parity_break_at_section_boundaries(bpm, swing, seed, last_cut):
    a = synth(bpm, 60, swing)
    timing, _ = generate_all(a, seed)
    for name in DIFFICULTIES:
        assert _dot_exit_case(a, timing, PROFILES[name], seed, last_cut) == [], name
