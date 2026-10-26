from saber_tooth.checks import check_difficulty
from saber_tooth.model import Color, Cut, Difficulty, Note, Wall
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing

T = Timing(120.0, [])


def found(notes, walls=(), name="Expert"):
    d = Difficulty(name, 16, 0, notes=sorted(notes), walls=list(walls))
    return {(f.rule, f.severity) for f in check_difficulty(d, T, PROFILES[name])}


def test_vertical_stack_is_fine():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.0, 1, 1, Color.RED, Cut.DOWN)]
    assert "stack-conflict" not in {r for r, _ in found(ns)}


def test_conflicting_cuts_in_stack_is_error():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.0, 1, 1, Color.RED, Cut.LEFT)]
    assert ("stack-conflict", "error") in found(ns)


def test_sideways_stack_against_swing_is_error():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.0, 2, 0, Color.RED, Cut.DOWN)]
    assert ("stack-conflict", "error") in found(ns)


def test_crossover_same_beat_is_error():
    ns = [Note(4.0, 3, 0, Color.RED, Cut.DOWN), Note(4.0, 0, 0, Color.BLUE, Cut.DOWN)]
    assert ("crossover", "error") in found(ns)


def test_crossover_near_is_warn():
    ns = [Note(4.0, 3, 0, Color.RED, Cut.DOWN), Note(4.5, 0, 0, Color.BLUE, Cut.UP)]
    assert ("crossover", "warn") in found(ns)


def test_no_crossover_when_sides_respected():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.0, 2, 0, Color.BLUE, Cut.DOWN)]
    assert "crossover" not in {r for r, _ in found(ns)}


def test_vision_block_is_error():
    ns = [Note(4.0, 1, 1, Color.RED, Cut.DOWN), Note(4.25, 3, 0, Color.BLUE, Cut.DOWN)]
    assert ("vision-block", "error") in found(ns)


def test_vision_block_absent_for_far_note():
    ns = [Note(4.0, 1, 1, Color.RED, Cut.DOWN), Note(6.0, 3, 0, Color.BLUE, Cut.DOWN)]
    assert "vision-block" not in {r for r, _ in found(ns)}


def test_vision_block_absent_off_centre_row():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.25, 3, 0, Color.BLUE, Cut.DOWN)]
    assert "vision-block" not in {r for r, _ in found(ns)}


def test_note_in_wall_is_error():
    ns = [Note(5.0, 1, 0, Color.RED, Cut.DOWN)]
    assert ("note-in-wall", "error") in found(ns, [Wall(4.0, 1, 0, 2.0, 1, 3)])


def test_note_outside_wall_is_fine():
    ns = [Note(5.0, 2, 0, Color.RED, Cut.DOWN), Note(7.0, 1, 0, Color.RED, Cut.UP)]
    assert "note-in-wall" not in {r for r, _ in found(ns, [Wall(4.0, 1, 0, 2.0, 1, 3)])}


def _dot_pair_swings(history):
    pair = [Note(8.0, 1, 1, Color.RED, Cut.ANY), Note(8.0, 2, 1, Color.RED, Cut.ANY)]
    return found([*history, *pair])


def test_horizontal_dot_pair_ignores_history():
    for cut in (Cut.DOWN, Cut.LEFT):
        prior = [Note(4.0, 1, 0, Color.RED, cut)]
        assert "stack-conflict" not in {r for r, _ in _dot_pair_swings(prior)}
    assert "stack-conflict" not in {r for r, _ in _dot_pair_swings([])}


def test_far_dot_pair_still_error():
    ns = [Note(4.0, 0, 0, Color.RED, Cut.ANY), Note(4.0, 3, 2, Color.RED, Cut.ANY)]
    assert ("stack-conflict", "error") in found(ns)


def _unsorted(ns):
    d = Difficulty("Expert", 16, 0, notes=list(ns))
    return {(f.rule, f.severity) for f in check_difficulty(d, T, PROFILES["Expert"])}


def test_unsorted_notes_still_flagged():
    cross = [Note(4.5, 0, 0, Color.BLUE, Cut.UP), Note(4.0, 3, 0, Color.RED, Cut.DOWN)]
    assert ("crossover", "warn") in _unsorted(cross)
    vis = [Note(4.25, 3, 0, Color.BLUE, Cut.DOWN), Note(4.0, 1, 1, Color.RED, Cut.DOWN)]
    assert ("vision-block", "error") in _unsorted(vis)


def test_crossover_one_finding_per_completing_note():
    ns = [
        Note(4.0, 3, 0, Color.RED, Cut.DOWN),
        Note(4.0, 3, 1, Color.RED, Cut.DOWN),
        Note(4.25, 0, 0, Color.BLUE, Cut.DOWN),
    ]
    d = Difficulty("Expert", 16, 0, notes=sorted(ns))
    fs = [f for f in check_difficulty(d, T, PROFILES["Expert"]) if f.rule == "crossover"]
    assert len(fs) == 1


def test_crossover_error_boundary_is_strict():
    # Expert error cross window 0.20s = 0.4 beats at 120 bpm
    at = [Note(4.0, 3, 0, Color.RED, Cut.DOWN), Note(4.4, 0, 0, Color.BLUE, Cut.UP)]
    inside = [Note(4.0, 3, 0, Color.RED, Cut.DOWN), Note(4.3, 0, 0, Color.BLUE, Cut.UP)]
    assert ("crossover", "warn") in found(at)
    assert ("crossover", "error") in found(inside)
