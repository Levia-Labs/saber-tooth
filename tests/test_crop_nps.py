import pytest

from saber_tooth.crop.nps import all_series, mean_nps, note_beats, nps_series, peak, slope
from saber_tooth.model import Bomb
from saber_tooth.timing import Timing
from tests.crop_helpers import beatmap, diff


def _chain_diff():
    d = diff("Expert", [0.0, 1.0])  # notes (0.0, x0, y0, red) and (1.0, x1, y0, blue)
    d.bombs = [Bomb(0.0, 0, 0), Bomb(1.5, 1, 1)]
    d.raw = {
        "sliders": [{"b": 0.0, "tb": 1.0, "x": 0, "y": 0, "c": 0, "tx": 1, "ty": 0}],
        "burstSliders": [
            {"b": 1.0, "tb": 3.0, "x": 1, "y": 0, "c": 1, "tx": 2, "ty": 1, "sc": 4},
            {"b": 2.0, "tb": 4.0, "x": 3, "y": 1, "c": 0, "tx": 2, "ty": 1, "sc": 4},
        ],
    }
    return d


def test_bombs_and_arcs_are_excluded_and_a_chain_counts_once():
    assert note_beats(_chain_diff()) == [0.0, 1.0, 2.0]  # the second chain has no head note


def test_nps_series_counts_per_second_bin():
    series = nps_series(_chain_diff(), Timing(120.0, []), 3.0)
    assert series == [2.0, 1.0, 0.0]


def test_notes_after_the_song_end_are_dropped():
    assert nps_series(diff("Expert", [0.0, 100.0]), Timing(120.0, []), 2.0) == [1.0, 0.0]


def test_all_series_lists_only_difficulties_with_notes():
    bm = beatmap(Easy=diff("Easy", []), Expert=diff("Expert", [0.0]))
    assert list(all_series(bm, Timing(120.0, []), 2.0)) == ["Expert"]


def test_mean_nps_weights_partial_bins():
    series = [2.0, 4.0, 6.0, 8.0]
    assert mean_nps(series, 0.0, 4.0) == pytest.approx(5.0)
    assert mean_nps(series, 0.5, 1.5) == pytest.approx(3.0)
    assert mean_nps(series, 3.0, 3.0) == 0.0
    assert peak(series) == 8.0 and peak([]) == 0.0


def test_slope_is_the_least_squares_trend():
    assert slope([1.0, 2.0, 3.0, 4.0], 0.0, 4.0) == pytest.approx(1.0)
    assert slope([3.0, 3.0, 3.0], 0.0, 3.0) == pytest.approx(0.0)
    assert slope([4.0, 3.0, 2.0, 1.0], 0.0, 4.0) == pytest.approx(-1.0)
    assert slope([5.0], 0.0, 1.0) == 0.0
