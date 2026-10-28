import math

from saber_tooth.analysis import Analysis
from saber_tooth.crop.nps import nps_series
from saber_tooth.crop.phrases import Grid, build_grid, grid_timing, hardest
from saber_tooth.crop.sections import change_scores, find_sections, pick_boundaries
from tests.crop_helpers import stepped_map

DURATION = 80.0  # stepped_map(40) at 120 bpm: last note at beat 157, song end at beat 160


def test_change_scores_find_clear_energy_steps():
    grid = Grid(0.0, 192.0)

    def features(lo: float, hi: float) -> list[float]:
        return [1.0 if 64.0 <= lo < 128.0 else 0.0]  # a loud chorus from beat 64 to 128

    scored = change_scores(grid, features)
    assert scored == [(32.0, 0.0), (64.0, 1.0), (96.0, 0.0), (128.0, 1.0), (160.0, 0.0)]
    assert pick_boundaries(grid, scored) == [0.0, 64.0, 128.0, 192.0]


def test_a_boundary_closer_than_eight_bars_keeps_the_higher_score():
    grid = Grid(0.0, 192.0)
    scored = [(32.0, 0.9), (48.0, 0.95), (96.0, 0.1), (128.0, 0.1), (160.0, 0.1)]
    assert pick_boundaries(grid, scored) == [0.0, 48.0, 192.0]


def test_the_song_end_beats_a_boundary_closer_than_eight_bars():
    grid = Grid(0.0, 144.0)
    scored = [(32.0, 0.5), (64.0, 0.9), (96.0, 0.1), (128.0, 0.95)]
    assert pick_boundaries(grid, scored) == [0.0, 144.0]


def test_a_flat_or_tiny_song_has_no_inner_boundary():
    assert pick_boundaries(Grid(0.0, 192.0), [(32.0, 0.0), (64.0, 0.0)]) == [0.0, 192.0]
    assert pick_boundaries(Grid(0.0, 6.0), []) == [0.0]


def _sections(bm, analysis):
    grid = build_grid(bm, DURATION)
    timing = grid_timing(bm)
    series = nps_series(hardest(bm), timing, DURATION)
    return find_sections(bm, grid, timing, analysis, series)


def test_without_analysis_sections_are_map_only():
    bm = stepped_map(bars=40, density=(1, 1, 3, 3, 2))
    result = _sections(bm, None)
    assert result.map_only is True
    # candidates are beats 32, 64, 96, 128 with scores 0, 1, 0, 0.5; only 1 is above the 70th
    # percentile (0.55); the last bar line of an 80 s song at 120 bpm is beat 160
    assert result.boundaries == [0.0, 64.0, 160.0]
    assert [s.start_beat for s in result.sections] == [0.0, 64.0]
    assert all(0.0 <= s.intensity <= 1.0 for s in result.sections)
    assert result.sections[1].nps > result.sections[0].nps


def test_audio_terms_find_a_step_the_map_does_not_show():
    bm = stepped_map(bars=40, density=(2,))  # flat map: no step in notes or lights
    kick = [32.0 + i * 0.25 for i in range(190)]  # drums enter at 32 s = beat 64
    analysis = Analysis("x", "C", 120.0, [], kick, [], [], None)
    assert _sections(bm, None).boundaries == [0.0, 160.0]
    with_audio = _sections(bm, analysis)
    assert with_audio.map_only is False
    assert with_audio.boundaries == [0.0, 64.0, 160.0]


def test_pitched_terms_count_when_present():
    bm = stepped_map(bars=40, density=(2,))
    melody = [32.0 + i * 0.5 for i in range(90)]
    ids = [50 + (i % 7) for i in range(90)]
    analysis = Analysis("x", "C", 120.0, [], [], [], [], None, [], [], melody, ids)
    result = _sections(bm, analysis)
    assert result.boundaries == [0.0, 64.0, 160.0]
    assert math.isclose(sum(s.end_beat - s.start_beat for s in result.sections), 160.0)
