"""Difficulties derived by thinning a denser one: walls and light show stay playable."""

from saber_tooth import fixer as fx
from saber_tooth.model import BasicEvent, Wall
from tests.test_fixer import dense_map, missing


def test_thinned_difficulty_drops_walls_the_tier_cannot_keep():
    short = Wall(900.0, 3, 2, 0.05, 1, 3)  # shorter than 0.12 s at 120 BPM
    ok = Wall(950.0, 3, 2, 4.0, 1, 3)
    m = dense_map(walls=[short, ok])
    hard = fx.apply_ops(m, fx.propose(m, missing(m, "Hard"), None, None, 1).ops).difficulties[
        "Hard"
    ]
    assert hard.walls == [ok]
    easy = fx.apply_ops(m, fx.propose(m, missing(m, "Easy"), None, None, 1).ops).difficulties[
        "Easy"
    ]
    assert easy.walls == []


def test_thinned_difficulty_does_not_inherit_a_strobing_show():
    from saber_tooth.checks import run_checks

    m = dense_map()
    d = m.difficulties["ExpertPlus"]
    d.events = [BasicEvent(8 + i * 0.05, 1, 1 + i % 2) for i in range(60)]  # flashes every 25 ms
    assert any(f.rule == "light-strobe" for f in run_checks(m, None, rules={"light-strobe"}))
    fixed = fx.apply_ops(m, fx.propose(m, missing(m, "Hard"), None, None, 1).ops)
    assert not [
        f for f in run_checks(fixed, None, rules={"light-strobe"}) if f.difficulty == "Hard"
    ]


def test_thinned_difficulty_gets_rest_zones_on_a_long_dense_map():
    from saber_tooth.checks import check_difficulty
    from saber_tooth.model import Color, Cut, Note
    from saber_tooth.profiles import PROFILES
    from saber_tooth.timing import Timing
    from tests.test_fixer import bm

    cuts = [Cut.DOWN if i % 2 == 0 else Cut.UP for i in range(900)]
    notes = [
        Note(8 + i * 0.5, 1 + i % 2, int(c == Cut.UP), Color(i % 2), c) for i, c in enumerate(cuts)
    ]
    m = bm(notes, "ExpertPlus")
    out = fx.propose(m, missing(m, "Hard"), None, None, 1)
    assert out is not None
    hard = fx.apply_ops(m, out.ops).difficulties["Hard"]
    found = check_difficulty(hard, Timing(120.0, []), PROFILES["Hard"], rules={"no-rest"})
    assert found == []
