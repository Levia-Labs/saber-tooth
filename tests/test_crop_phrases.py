import pytest

from saber_tooth.analysis import Analysis
from saber_tooth.crop.errors import NoNotes
from saber_tooth.crop.phrases import (
    build_grid,
    grid_drift,
    grid_events,
    grid_timing,
    hardest,
    tempo_at,
)
from saber_tooth.model import BpmEvent
from saber_tooth.timing import Timing
from tests.crop_helpers import beatmap, diff


def test_phrase_grid_with_bpm_change():
    bm = beatmap(Expert=diff("Expert", [5.5, 9.0], bpm_events=[BpmEvent(40.0, 60.0)]))
    grid = build_grid(bm, 60.0)
    assert grid.anchor == 4.0
    assert grid.end_beat == pytest.approx(80.0)  # 20 s at 120 bpm, then 40 s at 60 bpm
    assert grid.bars[0] == 4.0 and grid.bars[-1] == 80.0 and len(grid.bars) == 20
    assert grid.phrase_starts == [4.0, 36.0, 68.0]


def test_anchor_skips_a_note_free_intro():
    bm = beatmap(Expert=diff("Expert", [21.0]))
    assert build_grid(bm, 100.0).anchor == 20.0


def test_anchor_is_zero_when_notes_start_at_once():
    assert build_grid(beatmap(Expert=diff("Expert", [0.0, 1.0])), 30.0).anchor == 0.0


def test_grid_events_come_from_the_hardest_difficulty_with_notes():
    bm = beatmap(
        Easy=diff("Easy", [1.0], bpm_events=[BpmEvent(8.0, 90.0)]),
        Expert=diff("Expert", [1.0], bpm_events=[BpmEvent(8.0, 100.0)]),
        ExpertPlus=diff("ExpertPlus", []),
    )
    assert grid_events(bm) == [BpmEvent(8.0, 100.0)]
    assert hardest(bm).name == "Expert"


def test_a_map_without_notes_raises_no_notes():
    with pytest.raises(NoNotes):
        build_grid(beatmap(Expert=diff("Expert", [])), 30.0)
    with pytest.raises(NoNotes):
        build_grid(beatmap(), 30.0)


def test_tempo_at_follows_timing_rules():
    changes = [BpmEvent(40.0, 60.0), BpmEvent(0.0, 90.0)]
    assert tempo_at(120.0, changes, 0.0) == 90.0  # a change at beat 0 overrides the base
    assert tempo_at(120.0, changes, 39.99) == 90.0
    assert tempo_at(120.0, changes, 40.0) == 60.0
    assert tempo_at(120.0, [], 500.0) == 120.0


def test_tempo_at_matches_the_timing_slope():
    changes = [BpmEvent(8.0, 60.0), BpmEvent(24.0, 180.0)]
    timing = Timing(120.0, changes)
    for beat in (0.0, 7.0, 8.0, 20.0, 24.0, 30.0):
        bpm = tempo_at(120.0, changes, beat)
        assert timing.to_seconds(beat + 1) - timing.to_seconds(beat) == pytest.approx(60.0 / bpm)


def _analysis(beats: list[float]) -> Analysis:
    return Analysis("x", "C", 120.0, beats, [], [], [], None)


def test_grid_drift_is_the_median_distance_to_the_nearest_analyser_beat():
    bm = beatmap(Expert=diff("Expert", [0.0]))
    grid = build_grid(bm, 20.0)  # a bar line every 2 s
    timing = grid_timing(bm)
    aligned = _analysis([i * 0.5 for i in range(41)])
    shifted = _analysis([i * 0.5 + 0.2 for i in range(41)])
    assert grid_drift(grid, timing, aligned) == pytest.approx(0.0)
    assert grid_drift(grid, timing, shifted) == pytest.approx(0.2)
    assert grid_drift(grid, timing, None) is None
    assert grid_drift(grid, timing, _analysis([])) is None
