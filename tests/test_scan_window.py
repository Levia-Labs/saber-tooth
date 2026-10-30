"""Scan batches are checked on their own window and still cover the whole-difficulty findings."""

from saber_tooth.checks import MAP_RULES, run_checks
from saber_tooth.fixer import window
from saber_tooth.service.scan import _batches
from tests.test_checks_window import _ident, busy
from tests.test_fix_window import messy
from tests.test_fixer import bm


def test_batched_scan_findings_equal_the_whole_check(monkeypatch):
    monkeypatch.setattr(window, "BATCH_NOTES", 25)
    m = bm(messy(400, 2, 0.12))
    for analysis in (None, busy(80)):
        got = [f for _, fs in _batches(None, m, analysis) for f in fs]
        want = run_checks(m, analysis, rules=set(MAP_RULES)) + run_checks(
            m, analysis, difficulty="Expert"
        )
        assert sorted(map(_ident, got)) == sorted(map(_ident, want))
