import math
from itertools import pairwise

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.crop.phrases import Grid
from saber_tooth.crop.sections import Section, SectionMap
from saber_tooth.crop.window import (
    KINDS,
    TARGETS,
    WEIGHT_BUILD,
    band,
    build_plan,
    build_up,
    window_score,
)
from saber_tooth.model import BpmEvent
from saber_tooth.timing import Timing


def layout(bars=100, bpm=120.0, boundaries=(0.0, 128.0, 256.0), events=()):
    grid = Grid(0.0, bars * 4.0)
    timing = Timing(bpm, list(events))
    bounds = list(boundaries)
    sections = SectionMap(bounds, [Section(a, b, 1.0, 0.5) for a, b in pairwise(bounds)], True)
    duration = timing.to_seconds(grid.end_beat)
    series = [1.0] * math.ceil(duration)
    return grid, timing, sections, series, duration


def plan(target=60, **kw):
    grid, timing, sections, series, duration = layout(**kw)
    return build_plan(grid, sections, series, timing, target, duration)


def triples(p):
    return [(w.start_beat, w.end_beat, w.end_kind) for w in p.suggestions]


def test_bands_are_ten_percent_of_the_target():
    assert band(60) == (54.0, 66.0) and band(120) == (108.0, 132.0)


def test_end_prefers_a_section_boundary_inside_the_band():
    assert triples(plan()) == [
        (0.0, 128.0, "section"),
        (128.0, 256.0, "section"),
        (256.0, 384.0, "phrase"),  # a start with no section end in the band falls back
    ]


def test_end_falls_back_to_a_phrase_start():
    assert triples(plan(boundaries=(0.0, 200.0)))[0] == (0.0, 128.0, "phrase")


def test_end_falls_back_to_a_four_bar_line_then_a_bar_line():
    four = plan(bpm=110.0, boundaries=(0.0,))  # band is bars 25 to 30: no multiple of 8
    assert triples(four) == [(0.0, 112.0, "bar4")]
    one = plan(bpm=240.0 / 4.2, boundaries=(0.0,))  # band is bars 13 to 15: no multiple of 4
    assert triples(one) == [(0.0, 56.0, "bar")]


def test_band_is_measured_in_seconds_across_a_tempo_change():
    p = plan(bars=100, boundaries=(0.0,), events=[BpmEvent(64.0, 60.0)])
    # 64 beats take 32 s at 120 bpm, then one beat per second: 54 to 66 s is beats 86 to 98
    assert [e.beat for e in p.starts[0].ends] == [88.0, 92.0, 96.0]
    assert triples(p) == [(0.0, 96.0, "phrase")]


def test_every_suggestion_and_every_end_lies_inside_the_band():
    for target in TARGETS:
        p = plan(target=target, bars=200, boundaries=(0.0, 128.0, 256.0, 384.0, 512.0))
        lo, hi = band(target)
        assert p.enabled and 1 <= len(p.suggestions) <= 3
        for w in p.suggestions:
            assert lo <= w.length_s <= hi
        for s in p.starts:
            assert all(lo - 1e-6 <= e.seconds - s.seconds <= hi + 1e-6 for e in s.ends)


def test_a_song_shorter_than_the_band_disables_the_length():
    p = plan(bars=20)  # 40 s
    assert p.enabled is False and p.suggestions == [] and p.starts == []
    assert "40 s" in (p.reason or "") and "66 s" in (p.reason or "")


def test_window_score_pins_the_weights():
    assert window_score(4.0, 8.0, 0.5, "section") == pytest.approx(0.7 * 0.5 + 0.3 * 0.5)
    assert window_score(4.0, 8.0, 0.5, "phrase") == pytest.approx(0.7 * 0.5 + 0.3 * 0.5 - 0.1)
    assert window_score(4.0, 0.0, 0.0, "bar") == pytest.approx(-0.1)


def test_build_up_needs_a_lower_first_section_with_a_rising_slope():
    timing = Timing(120.0, [])
    sections = SectionMap(
        [0.0, 128.0, 256.0],
        [Section(0.0, 128.0, 2.0, 0.25), Section(128.0, 256.0, 6.0, 0.75)],
        True,
    )
    rising = [i * 0.1 for i in range(128)]
    falling = [10.0 - i * 0.05 for i in range(128)]
    assert build_up(sections, 0.0, rising, timing, 8.0) == pytest.approx(0.5)  # (6 - 2) / 8
    assert build_up(sections, 0.0, falling, timing, 8.0) == 0.0
    assert build_up(sections, 128.0, rising, timing, 8.0) == 0.0  # no section after the last
    higher_first = SectionMap(
        [0.0, 128.0, 256.0],
        [Section(0.0, 128.0, 6.0, 0.75), Section(128.0, 256.0, 2.0, 0.25)],
        True,
    )
    assert build_up(higher_first, 0.0, rising, timing, 8.0) == 0.0


def test_a_build_up_adds_its_bonus_to_the_window_score():
    grid, timing, _, series, duration = layout(bars=100, boundaries=(0.0, 128.0, 256.0))
    rising = [min(8.0, i * 0.2) for i in range(len(series))]  # peak 8
    flat = SectionMap(
        [0.0, 128.0, 256.0],
        [Section(0.0, 128.0, 4.0, 0.5), Section(128.0, 256.0, 4.0, 0.5)],
        True,
    )
    build = SectionMap(
        [0.0, 128.0, 256.0],
        [Section(0.0, 128.0, 2.0, 0.25), Section(128.0, 256.0, 6.0, 0.75)],
        True,
    )

    def at_start(sections):
        suggestions = build_plan(grid, sections, rising, timing, 60, duration).suggestions
        return next(w for w in suggestions if w.start_beat == 0.0)

    # the same window and mean NPS; only the bonus (6 - 2) / 8 = 0.5 differs
    assert at_start(build).score == pytest.approx(at_start(flat).score + WEIGHT_BUILD * 0.5)


@settings(max_examples=150, deadline=None)
@given(
    bars=st.integers(20, 160),
    bpm=st.floats(60.0, 240.0),
    picks=st.lists(st.integers(0, 40), max_size=8),
    values=st.lists(st.floats(0.0, 12.0), min_size=1, max_size=20),
    target=st.sampled_from(TARGETS),
)
def test_suggestions_lie_inside_the_band_and_start_on_boundaries(bars, bpm, picks, values, target):
    grid = Grid(0.0, bars * 4.0)
    timing = Timing(bpm, [])
    duration = timing.to_seconds(grid.end_beat)
    starts = sorted({0.0} | {32.0 * p for p in picks if 32.0 * p < grid.end_beat})
    sections = SectionMap(
        starts,
        [Section(a, b, values[i % len(values)], 0.0) for i, (a, b) in enumerate(pairwise(starts))],
        True,
    )
    series = [values[i % len(values)] for i in range(math.ceil(duration))]
    result = build_plan(grid, sections, series, timing, target, duration)
    lo, hi = band(target)
    for w in result.suggestions:
        assert lo - 1e-6 <= w.length_s <= hi + 1e-6
        assert any(abs(w.start_beat - b) < 1e-6 for b in starts)
        assert w.end_kind in KINDS
    for s in result.starts:
        assert any(abs(s.beat - b) < 1e-6 for b in starts)
        assert all(lo - 1e-6 <= e.seconds - s.seconds <= hi + 1e-6 for e in s.ends)


def test_no_sections_yield_no_windows_without_raising():
    grid, timing, _, series, duration = layout(bars=100, boundaries=(0.0,))
    empty = SectionMap([], [], True)
    p = build_plan(grid, empty, series, timing, 60, duration)
    assert p.enabled is False and p.suggestions == [] and p.starts == []
    assert p.reason
