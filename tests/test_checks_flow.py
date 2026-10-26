from saber_tooth.checks import check_difficulty
from saber_tooth.model import Bomb, BpmEvent, Color, Cut, Difficulty, Note
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing

T = Timing(120.0, [])


def rules(notes, name="Expert"):
    d = Difficulty(name, 16, 0, notes=sorted(notes))
    return {(f.rule, f.severity) for f in check_difficulty(d, T, PROFILES[name])}


def test_split_same_colour_is_error():
    ns = [Note(4.0, 0, 0, Color.RED, Cut.DOWN), Note(4.0, 3, 2, Color.RED, Cut.DOWN)]
    assert ("stack-conflict", "error") in rules(ns)


def test_clean_alternation_has_no_findings():
    ns = []
    for i in range(16):
        cut = Cut.DOWN if i % 2 == 0 else Cut.UP
        ns.append(Note(4.0 + i, 1, 0, Color.RED, cut))
        ns.append(Note(4.0 + i, 2, 0, Color.BLUE, cut))
    assert rules(ns) == set()


def test_double_down_fast_is_parity_error():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.5, 1, 0, Color.RED, Cut.DOWN)]
    assert ("parity-break", "error") in rules(ns)


def test_double_down_slow_is_fine():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(8.0, 1, 0, Color.RED, Cut.DOWN)]
    assert not {r for r, _ in rules(ns)} & {"parity-break"}


def test_far_jump_in_quarter_beat_is_error():
    ns = [Note(4.0, 0, 0, Color.RED, Cut.DOWN), Note(4.25, 3, 2, Color.RED, Cut.UP)]
    assert ("wide-jump", "error") in rules(ns)


def test_near_jump_is_fine():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(5.0, 0, 1, Color.RED, Cut.UP)]
    assert "wide-jump" not in {r for r, _ in rules(ns)}


def test_bomb_reset_allows_same_direction():
    d = Difficulty(
        "Expert",
        16,
        0,
        notes=[Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(5.0, 1, 0, Color.RED, Cut.DOWN)],
        bombs=[Bomb(4.5, 1, 2)],
    )
    assert not [f for f in check_difficulty(d, T, PROFILES["Expert"]) if f.rule == "parity-break"]


def test_bomb_in_other_half_does_not_reset():
    d = Difficulty(
        "Expert",
        16,
        0,
        notes=[Note(4.0, 0, 0, Color.RED, Cut.DOWN), Note(4.5, 0, 0, Color.RED, Cut.DOWN)],
        bombs=[Bomb(4.25, 3, 2)],
    )
    assert [f for f in check_difficulty(d, T, PROFILES["Expert"]) if f.rule == "parity-break"]


def test_swing_too_close_is_error():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.2, 1, 0, Color.RED, Cut.UP)]
    assert ("swing-speed", "error") in rules(ns)


def test_swing_warn_band():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.4, 1, 0, Color.RED, Cut.UP)]
    assert ("swing-speed", "warn") in rules(ns)


def test_swing_spaced_is_fine():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(5.0, 1, 0, Color.RED, Cut.UP)]
    assert "swing-speed" not in {r for r, _ in rules(ns)}


def _swing_speed(timing):
    ns = [Note(8.0, 1, 0, Color.RED, Cut.DOWN), Note(8.5, 1, 0, Color.RED, Cut.UP)]
    d = Difficulty("Expert", 16, 0, notes=ns)
    return {
        f.severity
        for f in check_difficulty(d, timing, PROFILES["Expert"])
        if f.rule == "swing-speed"
    }


def test_legal_pattern_becomes_swing_speed_error_after_tempo_increase():
    assert _swing_speed(Timing(120.0, [])) == set()
    assert _swing_speed(Timing(120.0, [BpmEvent(4.0, 480.0)])) == {"error"}


def test_fast_pattern_becomes_legal_after_tempo_decrease():
    assert _swing_speed(Timing(240.0, [])) == {"warn"}
    assert _swing_speed(Timing(240.0, [BpmEvent(4.0, 120.0)])) == set()


def test_compatible_mixed_cuts_trigger_parity_break():
    ns = [
        Note(4.0, 1, 0, Color.RED, Cut.DOWN),
        Note(4.0, 1, 1, Color.RED, Cut.DOWN_LEFT),
        Note(4.5, 1, 0, Color.RED, Cut.DOWN),
    ]
    assert ("parity-break", "error") in rules(ns)
