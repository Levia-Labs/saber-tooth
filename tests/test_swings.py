from saber_tooth.model import Color, Cut, Note
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing

T = Timing(120.0, [])


def test_stack_is_one_swing():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.DOWN), Note(1.0, 1, 1, Color.RED, Cut.DOWN)]
    s = build_swings(ns, T)[Color.RED]
    assert len(s) == 1 and s[0].start == (1, 1) and s[0].end == (1, 0)


def test_dot_infers_opposite():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.DOWN), Note(2.0, 1, 0, Color.RED, Cut.ANY)]
    s = build_swings(ns, T)[Color.RED]
    assert s[1].vector == (0, 1)


def test_first_dot_is_down():
    s = build_swings([Note(1.0, 1, 0, Color.RED, Cut.ANY)], T)[Color.RED]
    assert s[0].vector == (0, -1)


def test_hands_split():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.DOWN), Note(1.0, 2, 0, Color.BLUE, Cut.DOWN)]
    s = build_swings(ns, T)
    assert len(s[Color.RED]) == 1 and len(s[Color.BLUE]) == 1


def test_conflicting_cuts_give_no_vector():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.DOWN), Note(1.0, 2, 0, Color.RED, Cut.UP)]
    assert build_swings(ns, T)[Color.RED][0].vector is None


def test_mixed_any_uses_directional():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.ANY), Note(1.0, 1, 1, Color.RED, Cut.DOWN)]
    assert build_swings(ns, T)[Color.RED][0].vector == (0, -1)


def test_separate_beats_split():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.DOWN), Note(1.5, 1, 0, Color.RED, Cut.UP)]
    s = build_swings(ns, T)[Color.RED]
    assert [x.seconds for x in s] == [0.5, 0.75]


def test_profiles_table():
    assert list(PROFILES) == ["Easy", "Normal", "Hard", "Expert", "ExpertPlus"]
    e = PROFILES["Expert"]
    assert e.njs == 16 and e.grid == 0.25 and e.allow_dots and e.gap_beats == 8.0
    assert e.warn.min_hand_gap_s == 0.22 and e.error.vision_window_s == 0.18
    assert not PROFILES["Hard"].allow_dots and PROFILES["Hard"].allow_doubles


def test_dot_after_conflict_swing_infers_down():
    ns = [
        Note(1.0, 1, 0, Color.RED, Cut.DOWN),
        Note(2.0, 1, 0, Color.RED, Cut.DOWN),
        Note(2.0, 2, 0, Color.RED, Cut.UP),
        Note(3.0, 1, 0, Color.RED, Cut.ANY),
    ]
    s = build_swings(ns, T)[Color.RED]
    assert s[1].vector is None and s[2].vector == (0, -1)
