"""Swing-speed fixes keep the music covered: with audio, a deletion that opens an empty-gap is
no fix, so the strategy hands the fast second swing to the idle hand first."""

from saber_tooth import fixer as fx
from saber_tooth.analysis import Analysis
from saber_tooth.checks import run_checks
from saber_tooth.fixer import ops as fo
from saber_tooth.fixer.swing_fixes import delete_and_refill
from saber_tooth.fixer.verify import Context
from saber_tooth.model import Beatmap, Color, Cut, Difficulty, MapInfo, Note

BEATS = [i * 0.5 for i in range(60)]
BUSY = Analysis("x", "C major", 120.0, BEATS, BEATS, [], BEATS, None)
PLAY = [0, 7, 14, 21, 28, 29, 36, 43, 50, 57]  # every gap is under 8 beats


def _map() -> Beatmap:
    # beats 28 and 29 are 0.5 s apart: swing-speed warn on Easy
    notes = [Note(float(b), 1, 0, Color.RED, Cut.UP if b == 29 else Cut.DOWN) for b in PLAY]
    info = MapInfo("s", "", "a", "m", 120.0, "song.egg", "cover.png", 0, 10, "NiceEnvironment")
    return Beatmap(info, {"Easy": Difficulty("Easy", 16, 0, notes=notes)})


def _rules(m, analysis):
    return {f.rule for f in run_checks(m, analysis, difficulty="Easy")}


def test_fixture_reports_swing_speed_only():
    assert _rules(_map(), BUSY) == {"swing-speed"}


def test_deletion_that_opens_a_gap_is_refilled():
    m = _map()
    f = next(x for x in run_checks(m, BUSY, difficulty="Easy") if x.rule == "swing-speed")
    ctx = Context(m, f, BUSY, None, 1)
    late = next(n for n in m.difficulties["Easy"].notes if n.beat == 29.0)
    ops = delete_and_refill(ctx, [fo.Delete("Easy", late)])
    assert ops is not None and isinstance(ops[-1], fo.Fill)
    assert _rules(fx.apply_ops(m, ops), BUSY) == set()
    assert delete_and_refill(Context(m, f, None, None, 1), ops[:1]) is None  # needs audio


def test_swing_speed_fix_does_not_open_a_gap():
    m = _map()
    f = next(x for x in run_checks(m, BUSY, difficulty="Easy") if x.rule == "swing-speed")
    p = fx.propose(m, f, BUSY, None, 1)
    assert p is not None
    fixed = fx.apply_ops(m, p.ops)
    assert len(fixed.difficulties["Easy"].notes) == len(PLAY)  # nothing deleted
    assert _rules(fixed, BUSY) == set()
