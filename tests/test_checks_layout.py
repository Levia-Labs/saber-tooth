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
