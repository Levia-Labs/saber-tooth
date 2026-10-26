import pytest
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.checks import check_difficulty
from saber_tooth.model import Difficulty, Wall
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing

T = Timing(120.0, [])  # one beat is 0.5 s


def found(walls, name="Expert"):
    d = Difficulty(name, 16, 0, walls=sorted(walls))
    return {(f.rule, f.severity) for f in check_difficulty(d, T, PROFILES[name])}


def left(beat, dur=4.0):
    return Wall(beat, 0, 0, dur, 2, 5)


def right(beat, dur=4.0):
    return Wall(beat, 2, 0, dur, 2, 5)


def test_side_walls_on_both_edges_are_safe():
    walls = [Wall(4.0, 0, 0, 4.0, 1, 5), Wall(4.0, 3, 0, 4.0, 1, 5)]
    assert found(walls) == set()


def test_single_side_wall_is_safe():
    assert found([Wall(4.0, 3, 0, 2.0, 1, 5)]) == set()


def test_crouch_wall_is_safe():
    assert found([Wall(4.0, 1, 2, 2.0, 2, 3)]) == set()


def test_three_lanes_blocked_is_error():
    assert ("wall-trap", "error") in found([Wall(4.0, 0, 0, 2.0, 3, 5)])


def test_centre_lanes_blocked_is_error():
    assert ("wall-trap", "error") in found([Wall(4.0, 1, 0, 2.0, 2, 5)])


def test_two_walls_blocking_together_are_error():
    walls = [Wall(4.0, 0, 0, 4.0, 1, 5), Wall(5.0, 1, 0, 2.0, 2, 5)]
    assert ("wall-trap", "error") in found(walls)


def test_opposite_dodges_with_room_are_safe():
    assert found([left(4.0, 2.0), right(8.0)]) == set()  # 2 s gap


def test_opposite_dodges_warn_when_tight():
    # gap 1 beat = 0.5 s: below the Expert warn limit (0.6 s), above its error limit (0.36 s)
    assert ("wall-trap", "warn") in found([left(4.0, 2.0), right(7.0)])


def test_opposite_dodges_error_when_very_tight():
    assert ("wall-trap", "error") in found([left(4.0, 2.0), right(6.5)])


def test_same_side_dodges_are_safe():
    assert found([left(4.0, 2.0), left(6.0)]) == set()


@pytest.mark.parametrize(
    ("name", "gap_beats", "severity"),
    [("Hard", 1.2, "warn"), ("Hard", 0.8, "error"), ("ExpertPlus", 1.0, None)],
)
def test_dodge_time_depends_on_the_profile(name, gap_beats, severity):
    result = found([left(4.0, 2.0), right(6.0 + gap_beats)], name)
    assert (("wall-trap", severity) in result) if severity else ("wall-trap", "warn") not in result


def test_short_wall_is_warn():
    assert ("wall-short", "warn") in found([Wall(4.0, 0, 0, 0.1, 1, 5)])


def test_long_enough_wall_is_fine():
    assert "wall-short" not in {r for r, _ in found([Wall(4.0, 0, 0, 0.5, 1, 5)])}


walls_st = st.builds(
    Wall,
    st.floats(0, 64),
    st.integers(-2, 6),
    st.integers(-2, 6),
    st.floats(0, 16),
    st.integers(0, 6),
    st.integers(0, 6),
)


@given(st.lists(walls_st, max_size=12), st.sampled_from(sorted(PROFILES)))
def test_wall_rules_never_crash_on_arbitrary_walls(walls, name):
    assert all(r.startswith(("wall-", "note-in-wall")) for r, _ in found(walls, name))
