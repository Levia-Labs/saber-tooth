"""Two real-map cases (Feel Alive, Weight of the World): with the music analysed, a fix that
verifies exists for a swing pair 0.6 s apart and for a 10-beat gap after a long sparse stretch."""

from saber_tooth import fixer as fx
from saber_tooth.analysis import Analysis
from saber_tooth.checks import run_checks
from saber_tooth.model import Beatmap, Color, Cut, Difficulty, MapInfo, Note

INFO = MapInfo("s", "", "a", "m", 300.0, "song.egg", "cover.png", 0, 10, "NiceEnvironment")


def _analysis(bpm: float, end_beat: float) -> Analysis:
    step = 60.0 / bpm
    beats = [i * step for i in range(int(end_beat) + 1)]
    return Analysis("x", "C major", bpm, beats, beats, beats[::2], beats, None)


def _alternating(beats: list[float], x_of=lambda h: 1 if h == Color.RED else 2) -> list[Note]:
    notes, seen = [], {Color.RED: 0, Color.BLUE: 0}
    for i, b in enumerate(beats):
        hand = Color.RED if i % 2 == 0 else Color.BLUE
        cut = Cut.DOWN if seen[hand] % 2 == 0 else Cut.UP
        seen[hand] += 1
        notes.append(Note(float(b), x_of(hand), 0, hand, cut))
    return notes


def _outcome(notes: list[Note], bpm: float, end: float, rule: str):
    m = Beatmap(INFO, {"Easy": Difficulty("Easy", 16, 0, notes=notes)})
    m.info.bpm = bpm
    a = _analysis(bpm, end)
    found = [f for f in run_checks(m, a, difficulty="Easy") if f.rule == rule]
    assert found, "fixture must reproduce the finding"
    out = fx.propose_with_reason(m, found[0], a, None, 1)
    assert out.proposal is not None, out.reason
    fixed = fx.apply_ops(m, out.proposal.ops)
    assert not [f for f in run_checks(fixed, a, difficulty="Easy") if f.rule == rule]
    return fixed


def test_swing_pair_after_a_gap_is_fixed():
    beats = [*range(0, 293, 2), 299, 300, 302]
    _outcome(_alternating(beats), 300.0, 310, "swing-speed")


def test_ten_beat_gap_is_filled():
    beats = [*range(0, 194, 2), *range(203, 215, 2)]
    _outcome(_alternating(beats), 125.0, 215, "empty-gap")
