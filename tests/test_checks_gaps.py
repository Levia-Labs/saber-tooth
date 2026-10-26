from saber_tooth.analysis import Analysis
from saber_tooth.checks import RULES, check_difficulty
from saber_tooth.model import Color, Cut, Difficulty, Note
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing


def busy(seconds=60):
    k = [i * 0.5 for i in range(seconds * 2)]
    return Analysis("x", "C major", 120.0, k, k, [], k, None)


def _gaps(d, analysis):
    found = check_difficulty(d, Timing(120, []), PROFILES["Expert"], analysis)
    return [f for f in found if f.rule == "empty-gap"]


def _diff(*beats):
    ns = [Note(b, 1, 0, Color.RED, Cut.DOWN) for b in beats]
    return Difficulty("Expert", 16, 0, notes=ns)


def test_registered():
    assert "empty-gap" in RULES


def test_gap_with_music_is_flagged():
    f = _gaps(_diff(4.0, 40.0), busy())
    assert f and f[0].beat_start == 4.0 and f[0].beat_end == 40.0
    assert f[0].severity == "warn"


def test_gap_in_silence_is_fine():
    quiet = Analysis("x", "C major", 120.0, [i * 0.5 for i in range(120)], [], [], [], None)
    assert not _gaps(_diff(4.0, 40.0), quiet)


def test_no_analysis_skips():
    assert not _gaps(_diff(4.0, 40.0), None)


def test_leading_and_trailing_gaps():
    f = _gaps(_diff(20.0, 24.0), busy(30))
    assert [(x.beat_start, x.beat_end) for x in f] == [(0.0, 20.0), (24.0, 59.0)]


def test_short_gap_is_fine():
    assert not _gaps(_diff(0.0, 4.0, 8.0, 12.0), busy(6))


def test_zero_note_difficulty_is_one_gap_over_the_analysed_range():
    f = _gaps(Difficulty("Expert", 16, 0), busy(30))
    assert [(x.beat_start, x.beat_end) for x in f] == [(0.0, 59.0)]


def test_zero_note_difficulty_without_music_is_fine():
    assert not _gaps(Difficulty("Expert", 16, 0), Analysis("x", "C", 120.0, [], [], [], [], None))
