"""Finer fixer strategies: single-note deletes, dot-aware flips, joint multi-note moves."""

from saber_tooth import fixer as fx
from saber_tooth.fixer import ops as fo
from saber_tooth.model import Cut
from tests.test_fixer import _n, bm, find


def test_swing_speed_deletes_one_note_of_a_stack():
    notes = [_n(8, 0, 0), _n(8.41, 0, 1, cut=Cut.UP), _n(8.448, 1, 1, cut=Cut.UP)]
    m = bm(notes)
    p = fx.propose(m, find(m, "swing-speed"), None, None, 1)
    assert [type(o) for o in p.ops] == [fo.Delete]
    assert p.ops[0].note == notes[1]
    assert len(fx.apply_ops(m, p.ops).difficulties["Expert"].notes) == 2


def test_parity_break_keeps_dots_when_flipping_a_mixed_swing():
    notes = [_n(8, 1, 0), _n(8.5, 1, 0), _n(8.5, 2, 0, cut=Cut.ANY)]
    m = bm(notes)
    p = fx.propose(m, find(m, "parity-break"), None, None, 1)
    assert [(o.note.cut, o.cut) for o in p.ops] == [(Cut.DOWN, Cut.UP)]
    assert Cut.ANY in {n.cut for n in fx.apply_ops(m, p.ops).difficulties["Expert"].notes}


def test_wide_jump_moves_a_stack_as_a_unit():
    notes = [_n(8, 3, 1), _n(8.6, 0, 1, cut=Cut.UP), _n(8.6, 1, 1, cut=Cut.UP)]
    m = bm(notes)
    p = fx.propose(m, find(m, "wide-jump"), None, None, 1)
    assert [(o.x, o.y) for o in p.ops] == [(2, 1), (1, 1)]  # leading note first
    assert len(fx.apply_ops(m, p.ops).difficulties["Expert"].notes) == 3
