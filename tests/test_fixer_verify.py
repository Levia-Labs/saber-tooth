import dataclasses

from saber_tooth import fixer as fx
from saber_tooth.checks import run_checks
from saber_tooth.fixer import ops as fo
from saber_tooth.fixer.verify import Context, accepts
from saber_tooth.model import Cut
from tests.test_fixer import FLOW, _n, bm


def _chain():
    cuts = (Cut.DOWN, Cut.UP)
    return bm([_n(i * 0.5, 3 * (i % 2), 2 * (i % 2), cut=cuts[i % 2]) for i in range(4)])


def test_target_persisting_next_to_neighbour_findings_is_rejected():
    m = _chain()
    f = next(g for g in run_checks(m, rules=FLOW) if g.rule == "wide-jump")
    assert f.beat_start == 0
    move = fo.Move("Expert", _n(0.5, 3, 2, cut=Cut.UP), 2, 2, Cut.UP)
    assert accepts(Context(m, f, None, None, 1), [move]) is None


def test_new_findings_counts_severity_increase():
    m = _chain()
    warn = next(g for g in run_checks(m, rules=FLOW) if g.severity == "warn")
    worse = dataclasses.replace(warn, severity="error")
    assert fx.new_findings([worse], [warn]) == [worse]
    assert fx.new_findings([warn], [worse]) == []
    assert fx.new_findings([warn], [warn]) == []
