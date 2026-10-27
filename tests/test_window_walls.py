from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth import fixer as fx
from saber_tooth.checks import check_difficulty, run_checks
from saber_tooth.fixer import ops as fo
from saber_tooth.generator import generate_all, generate_difficulty
from saber_tooth.model import Color, Cut, Difficulty, Note, Wall
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import build_swings
from tests.test_fixer import bm, busy
from tests.test_generator_walls import calm_passage

WALL_RULES = {"wall-trap", "wall-short", "note-in-wall"}
LO, HI = 20.0, 36.0


def refill(a, seed, name, extra=()):
    """Regenerate the window of a generated difficulty; return the pieces and the merge."""
    timing, diffs = generate_all(a, seed)
    d, profile = diffs[name], PROFILES[name]
    secs = [timing.to_seconds(n.beat) for n in d.notes]
    before = [n for n, s in zip(d.notes, secs, strict=True) if s < LO]
    after = [n for n, s in zip(d.notes, secs, strict=True) if s >= HI]
    entry = {h: sw[-1] for h, sw in build_swings(before, timing).items() if sw}
    exit_ = {h: sw[0] for h, sw in build_swings(after, timing).items() if sw}
    walls = [*d.walls, *extra]
    fill = generate_difficulty(
        a, timing, profile, seed, window=(LO, HI), entry=entry, exit=exit_, walls=walls
    )
    merged = Difficulty(name, d.njs, d.offset, notes=sorted(before + fill.notes + after))
    merged.walls = fill.walls
    return timing, profile, d, fill, merged


def test_fill_keeps_a_wall_outside_the_window():
    a = calm_passage()
    timing, _, d, _, _ = refill(a, 3, "Hard")
    beat = timing.to_beats(HI + 6)
    outside = Wall(beat, 3, 0, 2.0, 1, 5)
    *_, fill, merged = refill(a, 3, "Hard", [outside])
    assert outside in fill.walls and d.walls
    assert all(w in merged.walls for w in d.walls if not LO < timing.to_seconds(w.beat) < HI)


def test_fill_drops_a_wall_a_new_note_sits_in():
    a = calm_passage()
    *_, fill, _ = refill(a, 3, "Hard")
    note = fill.notes[0]
    trap = Wall(note.beat - 0.5, note.x, 0, 1.0, 1, 5)
    _, _, _, again, _ = refill(a, 3, "Hard", [trap])
    inside = [n for n in again.notes if trap.beat <= n.beat <= trap.beat + 1.0 and n.x == trap.x]
    assert trap not in again.walls or not inside


@settings(max_examples=12, deadline=None)
@given(st.integers(0, 400), st.sampled_from(["Hard", "Expert", "ExpertPlus"]))
def test_fill_never_yields_wall_findings(seed, name):
    a = calm_passage()
    timing, profile, _, _, merged = refill(a, seed, name)
    assert check_difficulty(merged, timing, profile, a, WALL_RULES) == []


def test_fixer_fill_carries_wall_changes_and_keeps_far_walls():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(60.0, 2, 0, Color.BLUE, Cut.DOWN)]
    far = Wall(110.0, 3, 0, 2.0, 1, 5)
    m = bm(ns, walls=[far])
    a = busy()
    f = next(f for f in run_checks(m, a, difficulty="Expert") if f.rule == "empty-gap")
    p = fx.propose(m, f, a, None, 1)
    fill = p.ops[0]
    assert isinstance(fill, fo.Fill) and far not in fill.walls_removed
    fixed = fx.apply_ops(m, p.ops)
    assert far in fixed.difficulties["Expert"].walls
    assert fo.op_from_dict(fill.to_dict()) == fill
    assert not [x for x in run_checks(fixed, a, difficulty="Expert") if x.rule.startswith("wall")]
