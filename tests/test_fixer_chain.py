"""Chains of too-fast swings, where deleting one swing only moves the problem."""

from saber_tooth.checks import run_checks
from saber_tooth.model import Color, Cut
from saber_tooth.service.fix import fix_beatmap
from tests.test_fixer import _n, bm


def _chain(n: int):
    cuts = [Cut.DOWN, Cut.UP] * n
    return bm([_n(8 + i * 0.236, 1, 1, cut=c) for i, c in enumerate(cuts[:n])])


def test_swing_chain_reaches_zero_errors():
    for n in (3, 4, 5, 6):
        m = _chain(n)
        run = fix_beatmap(m, None, None, 1)
        errors = [
            f
            for f in run_checks(run.fixed)
            if f.severity == "error" and f.rule != "missing-difficulty"
        ]
        assert not errors, (n, [(f.rule, f.message) for f in errors])


def test_midnight_demons_swing_run_reaches_zero_errors():
    # Expert, 127 bpm, beats 222.3175 to 223.0675 of "347 Midnight Demons"
    cuts = [Cut.DOWN_RIGHT, Cut.LEFT, Cut.RIGHT, Cut.UP_LEFT]
    notes = [_n(222.3175 + i * 0.25, 3, 0, Color.BLUE, c) for i, c in enumerate(cuts)]
    notes += [
        _n(220.3175, 3, 0, Color.RED, Cut.RIGHT),
        _n(220.3175, 3, 1, Color.BLUE, Cut.RIGHT),
        _n(221.3175, 0, 0, Color.BLUE, Cut.LEFT),
        _n(221.3175, 0, 1, Color.RED, Cut.LEFT),
        _n(224.3175, 2, 0, Color.BLUE, Cut.DOWN),
    ]
    m = bm(notes)
    m.info.bpm = 127.0
    run = fix_beatmap(m, None, None, 1)
    errors = [f for f in run_checks(run.fixed) if f.severity == "error"]
    assert not [f for f in errors if f.rule != "missing-difficulty"]


def test_fix_beatmap_reports_each_round_it_runs():
    calls: list[tuple[int, int]] = []
    run = fix_beatmap(
        _chain(4), None, None, 1, max_rounds=2, on_round=lambda n, t: calls.append((n, t))
    )
    assert calls[0] == (1, 2)
    assert len(calls) == run.rounds
