"""A fill for an empty gap that is the map's only rest keeps that rest: two notes of one hand
close it without breaking either hand's alternation or the rest zone."""

from saber_tooth import fixer as fx
from saber_tooth.analysis import Analysis
from saber_tooth.checks import run_checks
from saber_tooth.model import Beatmap, Color, Cut, Difficulty, MapInfo, Note

BEATS = [i * 0.5 for i in range(100)]
BUSY = Analysis("x", "C major", 120.0, BEATS, BEATS, [], BEATS, None)
PLAY = [*range(0, 46), *range(55, 100)]  # a 9-beat gap, the only rest in 50 s of play


def _map() -> Beatmap:
    notes, seen = [], {Color.RED: 0, Color.BLUE: 0}
    for b in PLAY:
        hand = Color.RED if b % 2 == 0 else Color.BLUE
        cut = Cut.DOWN if seen[hand] % 2 == 0 else Cut.UP  # each hand alternates over the gap
        seen[hand] += 1
        notes.append(Note(float(b), 1 if hand == Color.RED else 2, 0, hand, cut))
    info = MapInfo("s", "", "a", "m", 120.0, "song.egg", "cover.png", 0, 10, "NiceEnvironment")
    return Beatmap(info, {"Expert": Difficulty("Expert", 16, 0, notes=notes)})


def _rules(m):
    return {f.rule for f in run_checks(m, BUSY, difficulty="Expert")}


def test_fixture_reports_the_gap_only():
    assert _rules(_map()) == {"empty-gap"}


def test_gap_fill_keeps_the_rest():
    m = _map()
    f = next(x for x in run_checks(m, BUSY, difficulty="Expert") if x.rule == "empty-gap")
    p = fx.propose(m, f, BUSY, None, 1)
    assert p is not None
    assert _rules(fx.apply_ops(m, p.ops)) == set()
