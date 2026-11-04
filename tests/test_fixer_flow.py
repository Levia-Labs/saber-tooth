"""Flow fixes that remove notes keep the hand's alternation intact."""

from saber_tooth import fixer as fx
from saber_tooth.checks import run_checks
from saber_tooth.fixer import ops as fo
from saber_tooth.fixer.strategies import wide_jump
from saber_tooth.fixer.verify import Context
from saber_tooth.model import Color, Cut, Note
from tests.test_fixer import bm, find

FLOW = {"parity-break", "wide-jump", "swing-speed"}


def stream():
    return bm(
        [
            Note(8.0, 0, 0, Color.RED, Cut.DOWN),
            Note(8.5, 3, 2, Color.RED, Cut.UP),
            Note(9.0, 0, 0, Color.RED, Cut.DOWN),
            Note(9.5, 1, 1, Color.RED, Cut.UP),
        ]
    )


def test_wide_jump_last_resort_drops_two_swings_before_one():
    m = stream()
    got = list(wide_jump(Context(m, find(m, "wide-jump"), None, None, 1)))
    assert all(isinstance(o, fo.Delete) for o in got[-1]) and len(got[-1]) == 1
    assert all(isinstance(o, fo.Delete) for o in got[-2]) and len(got[-2]) == 2


def test_wide_jump_fix_leaves_no_parity_break():
    m = stream()
    p = fx.propose(m, find(m, "wide-jump"), None, None, 1)
    assert p is not None
    assert "parity-break" not in {f.rule for f in run_checks(fx.apply_ops(m, p.ops), rules=FLOW)}


def test_vision_block_tries_every_free_cell_then_drops_the_note():
    from saber_tooth.fixer.layout_fixes import vision_block

    blocker = Note(8.0, 1, 1, Color.RED, Cut.DOWN)
    crowd = [Note(8.0, x, y, Color.BLUE, Cut.DOWN) for x, y in ((0, 1), (1, 0), (0, 0))]
    m = bm([blocker, *crowd, Note(8.25, 3, 1, Color.BLUE, Cut.UP)])
    got = list(vision_block(Context(m, find(m, "vision-block"), None, None, 1)))
    moves = [c[0] for c in got if isinstance(c[0], fo.Move)]
    assert len(moves) > 3 and all(not (o.x in (1, 2) and o.y == 1) for o in moves)
    assert all(isinstance(o, fo.Delete) for o in got[-1])


def test_note_converge_last_resort_keeps_the_hand_alternating():
    from saber_tooth.fixer.layout_fixes import note_converge

    m = bm(
        [
            Note(8.0, 0, 0, Color.RED, Cut.DOWN),
            Note(8.5, 0, 2, Color.RED, Cut.UP),
            Note(9.0, 1, 0, Color.RED, Cut.DOWN),
            Note(10.0, 2, 0, Color.RED, Cut.UP),
        ]
    )
    got = list(note_converge(Context(m, find(m, "note-converge"), None, None, 1)))
    deletes = [c for c in got if all(isinstance(o, fo.Delete) for o in c)]
    assert {len(c) for c in deletes} == {1, 2}  # a swing and its follower, then the swing alone
