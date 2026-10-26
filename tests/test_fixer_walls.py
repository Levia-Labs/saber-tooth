import pytest

from saber_tooth import fixer as fx
from saber_tooth.checks import run_checks
from saber_tooth.fixer import ops as fo
from saber_tooth.fixer.strategies import STRATEGIES
from saber_tooth.model import Wall
from tests.test_fixer import bm, find

BAD = Wall(8.0, 1, 0, 2.0, 2, 5)  # blocks both centre lanes
SHORT = Wall(8.0, 0, 0, 0.1, 1, 5)
GOOD = Wall(16.0, 3, 0, 2.0, 1, 5)


def test_both_wall_rules_have_a_strategy():
    assert {"wall-trap", "wall-short"} <= set(STRATEGIES)


@pytest.mark.parametrize(("rule", "wall"), [("wall-trap", BAD), ("wall-short", SHORT)])
def test_unsafe_wall_is_deleted_and_good_wall_kept(rule, wall):
    m = bm([], walls=[wall, GOOD])
    p = fx.propose(m, find(m, rule), None, None, 1)
    assert p is not None and p.ops == [fo.DeleteWall("Expert", wall)]
    fixed = fx.apply_ops(m, p.ops)
    assert fixed.difficulties["Expert"].walls == [GOOD]
    assert not [f for f in run_checks(fixed, difficulty="Expert") if f.rule.startswith("wall-")]
    assert m.difficulties["Expert"].walls == [wall, GOOD]  # input untouched


def test_delete_wall_round_trips_through_json_and_conflicts():
    op = fo.DeleteWall("Expert", BAD)
    assert fo.op_from_dict(op.to_dict()) == op
    with pytest.raises(fo.OpConflict):
        fx.apply_ops(bm([], walls=[GOOD]), [op])
    with pytest.raises(fo.OpConflict):
        fx.apply_ops(bm([], walls=[BAD]), [fo.DeleteWall("Missing", BAD)])


def test_delete_wall_is_summarised():
    p = fx.propose(bm([], walls=[BAD]), find(bm([], walls=[BAD]), "wall-trap"), None, None, 1)
    assert "Delete wall at beat 8" in p.summary


def test_tight_opposite_dodge_drops_the_later_wall():
    first, second = Wall(4.0, 0, 0, 2.0, 2, 5), Wall(7.0, 2, 0, 4.0, 2, 5)
    m = bm([], walls=[first, second])
    p = fx.propose(m, find(m, "wall-trap"), None, None, 1)
    assert p.ops == [fo.DeleteWall("Expert", second)]
