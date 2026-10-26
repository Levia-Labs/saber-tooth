import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.analysis import Analysis
from saber_tooth.checks import check_difficulty, run_checks
from saber_tooth.fixer import apply_ops, finding_key, op_from_dict, propose, propose_with_reason
from saber_tooth.fixer.ops import (
    AddDifficulty,
    ApplyLightshow,
    Delete,
    Fill,
    Flip,
    Move,
    OpConflict,
    Recolor,
)
from saber_tooth.lightshow import Templates, Unit
from saber_tooth.model import (
    BasicEvent,
    Beatmap,
    Bomb,
    BpmEvent,
    Color,
    ColorScheme,
    Cut,
    Difficulty,
    MapInfo,
    Note,
    Wall,
)
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing

FLOW = {"parity-break", "wide-jump", "swing-speed", "stack-conflict", "crossover", "vision-block"}


def bm(notes, name="Expert", env="NiceEnvironment", **kw):
    info = MapInfo("s", "", "a", "m", 120.0, "song.egg", "cover.png", 0, 10, env)
    return Beatmap(info, {name: Difficulty(name, 16, 0, notes=sorted(notes), **kw)})


def find(m, rule, name="Expert", analysis=None):
    return next(f for f in run_checks(m, analysis, difficulty=name) if f.rule == rule)


def left_ids(m, name="Expert", analysis=None):
    d = m.difficulties[name]
    fs = check_difficulty(d, Timing(120.0, d.bpm_events), PROFILES[name], analysis)
    return {(f.rule, f.beat_start, f.beat_end) for f in fs}


def test_split_stack_fixed():
    m = bm([Note(4.0, 0, 0, Color.RED, Cut.DOWN), Note(4.0, 3, 2, Color.RED, Cut.DOWN)])
    f = find(m, "stack-conflict")
    p = propose(m, f, None, None, 1)
    fixed = apply_ops(m, p.ops)
    assert not [g for g in run_checks(fixed, difficulty="Expert") if g.rule == "stack-conflict"]
    assert len(fixed.difficulties["Expert"].notes) == 2
    assert p.summary.startswith("Move red note at beat 4")


def test_apply_ops_is_pure():
    m = bm([Note(4.0, 0, 0, Color.RED, Cut.DOWN)])
    before = list(m.difficulties["Expert"].notes)
    out = apply_ops(m, [Delete("Expert", before[0])])
    assert out.difficulties["Expert"].notes == []
    assert m.difficulties["Expert"].notes == before


def test_conflict_when_note_missing():
    m = bm([Note(4.0, 0, 0, Color.RED, Cut.DOWN)])
    ghost = Note(9.0, 1, 1, Color.BLUE, Cut.UP)
    for op in (Delete("Expert", ghost), Flip("Expert", ghost, Cut.DOWN), Recolor("Expert", ghost)):
        with pytest.raises(OpConflict, match="not found"):
            apply_ops(m, [op])


def test_parity_break_flips_second_swing():
    notes = [Note(8.0, 1, 0, Color.RED, Cut.DOWN), Note(8.5, 1, 0, Color.RED, Cut.DOWN)]
    m = bm(notes)
    p = propose(m, find(m, "parity-break"), None, None, 1)
    assert isinstance(p.ops[0], Flip) and p.ops[0].cut == Cut.UP
    assert p.before == [notes[1]] and p.after[0].cut == Cut.UP


def test_wide_jump_moves_toward_previous_swing():
    notes = [Note(8.0, 0, 0, Color.RED, Cut.DOWN), Note(8.25, 3, 2, Color.RED, Cut.UP)]
    m = bm(notes)
    p = propose(m, find(m, "wide-jump"), None, None, 1)
    assert p is not None and "wide-jump" not in {r for r, *_ in left_ids(apply_ops(m, p.ops))}


def test_swing_speed_deletes_later_without_analysis():
    notes = [Note(8.0, 0, 0, Color.RED, Cut.DOWN), Note(8.05, 0, 1, Color.RED, Cut.UP)]
    m = bm(notes)
    p = propose(m, find(m, "swing-speed"), None, None, 1)
    assert [type(o) for o in p.ops] == [Delete] and p.ops[0].note == notes[1]


def test_crossover_recolors():
    notes = [Note(8.0, 3, 0, Color.RED, Cut.DOWN), Note(8.0, 0, 0, Color.BLUE, Cut.DOWN)]
    m = bm(notes)
    p = propose(m, find(m, "crossover"), None, None, 1)
    assert p is not None and all(isinstance(o, Recolor) for o in p.ops)


def test_vision_block_moves_centre_note_outward():
    notes = [Note(8.0, 1, 1, Color.RED, Cut.DOWN), Note(8.15, 3, 1, Color.BLUE, Cut.DOWN)]
    m = bm(notes)
    p = propose(m, find(m, "vision-block"), None, None, 1)
    assert isinstance(p.ops[0], Move) and (p.ops[0].x, p.ops[0].y) == (0, 1)


def test_note_in_wall_moves_to_free_lane():
    m = bm([Note(8.0, 1, 0, Color.RED, Cut.DOWN)], walls=[Wall(7.0, 1, 0, 2.0, 1, 3)])
    p = propose(m, find(m, "note-in-wall"), None, None, 1)
    fixed = apply_ops(m, p.ops)
    assert not [g for g in run_checks(fixed, difficulty="Expert") if g.rule == "note-in-wall"]
    assert isinstance(p.ops[0], Move)


def busy(seconds=60):
    k = [i * 0.5 for i in range(seconds * 2)]
    return Analysis("x", "C major", 120.0, k, k, k[1::2], k, None)


def test_empty_gap_filled_with_analysis_only():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(60.0, 2, 0, Color.BLUE, Cut.DOWN)]
    m = bm(ns)
    a = busy()
    f = find(m, "empty-gap", analysis=a)
    assert propose(m, f, None, None, 1) is None
    p = propose(m, f, a, None, 1)
    assert isinstance(p.ops[0], Fill) and p.after
    assert (f.rule, f.beat_start, f.beat_end) not in left_ids(apply_ops(m, p.ops), analysis=a)


def test_missing_difficulty_with_analysis_generates():
    m = bm([Note(4.0, 1, 0, Color.RED, Cut.DOWN)])
    a = busy(40)
    f = next(
        f for f in run_checks(m, a) if f.rule == "missing-difficulty" and f.difficulty == "Easy"
    )
    p = propose(m, f, a, None, 3)
    assert isinstance(p.ops[0], AddDifficulty)
    fixed = apply_ops(m, p.ops)
    assert "Easy" in fixed.difficulties and left_ids(fixed, "Easy", a) == set()


def dense_map(**kw):
    cuts = [Cut.DOWN if (i // 2) % 2 == 0 else Cut.UP for i in range(160)]
    ns = [Note(8 + i / 4, 1 + i % 2, int(c == Cut.UP), Color(i % 2), c) for i, c in enumerate(cuts)]
    return bm(ns, "ExpertPlus", **kw)


def test_missing_difficulty_thins_denser_without_analysis():
    m = dense_map()
    f = next(f for f in run_checks(m) if f.rule == "missing-difficulty" and f.difficulty == "Hard")
    out = propose_with_reason(m, f, None, None, 1)
    assert out.proposal is not None, out.reason
    fixed = apply_ops(m, out.proposal.ops)
    hard = fixed.difficulties["Hard"]
    assert 0 < len(hard.notes) < len(m.difficulties["ExpertPlus"].notes)
    assert left_ids(fixed, "Hard") == set()


def test_missing_difficulty_without_denser_needs_analysis():
    m = bm([Note(4.0, 1, 0, Color.RED, Cut.DOWN)], "Easy")
    f = next(f for f in run_checks(m) if f.rule == "missing-difficulty" and f.difficulty == "Hard")
    out = propose_with_reason(m, f, None, None, 1)
    assert out.proposal is None and out.reason == "needs analysis"


def templates():
    def unit(env, e):
        grp = {"b": 1.0, "g": 0, "e": [{"b": 0.0}]}
        return Unit(
            env, "a", e, [BasicEvent(0.5, 1, 2)], [(0.0, True)], {"lightColorEventBoxGroups": [grp]}
        )

    return Templates(
        {"EnvA": [unit("EnvA", e) for e in (0.1, 0.4, 0.7, 1.0)]}, {"EnvA": [ColorScheme("S", {})]}
    )


def test_default_environment():
    m = bm(
        [Note(4.0 + i, 1, 0, Color.RED, Cut.DOWN) for i in range(0, 40, 2)],
        env="DefaultEnvironment",
    )
    f = run_checks(m, rules={"default-environment"})[0]
    assert propose(m, f, None, None, 1) is None
    assert propose(m, f, None, Templates(), 1) is None
    p = propose(m, f, None, templates(), 1)
    fixed = apply_ops(m, p.ops)
    assert fixed.info.environment == "EnvA" and fixed.difficulties["Expert"].events
    assert not run_checks(fixed, rules={"default-environment"})
    assert m.info.environment == "DefaultEnvironment"


notes = st.builds(
    Note,
    beat=st.integers(8, 200).map(lambda i: i / 4),
    x=st.integers(0, 3),
    y=st.integers(0, 2),
    color=st.sampled_from(Color),
    cut=st.sampled_from([c for c in Cut if c != Cut.ANY]),
)


@settings(max_examples=60, deadline=None)
@given(st.lists(notes, min_size=2, max_size=30))
def test_fix_removes_finding_and_adds_none(ns):
    m = bm(ns)
    before = {finding_key(f) for f in run_checks(m, rules=FLOW)}
    for f in run_checks(m, rules=FLOW):
        p = propose(m, f, None, None, 1)
        if p is None:
            continue
        after = {finding_key(g) for g in run_checks(apply_ops(m, p.ops), rules=FLOW)}
        assert finding_key(f) not in after
        assert after <= before


small = st.integers(0, 6)
beats = st.floats(0, 500, allow_nan=False, allow_infinity=False)
cells = st.builds(Note, beats, small, small, st.sampled_from(Color), st.sampled_from(Cut), small)
raw_groups = st.dictionaries(
    st.sampled_from(["lightColorEventBoxGroups", "vfxEventBoxGroups"]),
    st.lists(st.fixed_dictionaries({"b": beats, "g": small}), max_size=3),
)
events = st.builds(BasicEvent, beats, small, small, st.floats(0, 2, allow_nan=False))
boosts = st.lists(st.tuples(beats, st.booleans()), max_size=3)
lightshows = st.builds(
    ApplyLightshow,
    st.text(max_size=8),
    st.one_of(st.none(), st.builds(ColorScheme, st.text(max_size=4), st.just({"a": {"r": 0.5}}))),
    st.dictionaries(
        st.text(max_size=5), st.tuples(st.lists(events, max_size=3), boosts, raw_groups), max_size=2
    ),
)
difficulties = st.builds(
    Difficulty,
    st.sampled_from(["Easy", "Expert"]),
    st.floats(1, 30, allow_nan=False),
    st.floats(-1, 1, allow_nan=False),
    st.lists(cells, max_size=4),
    st.lists(st.builds(Bomb, beats, small, small), max_size=2),
    st.lists(st.builds(Wall, beats, small, small, beats, small, small), max_size=2),
    st.lists(events, max_size=2),
    boosts,
    st.lists(st.builds(BpmEvent, beats, st.floats(60, 200, allow_nan=False)), max_size=2),
    raw_groups,
    st.text(max_size=6),
)
ops = st.one_of(
    st.builds(Move, st.text(max_size=5), cells, small, small, st.sampled_from(Cut)),
    st.builds(Recolor, st.text(max_size=5), cells),
    st.builds(Flip, st.text(max_size=5), cells, st.sampled_from(Cut)),
    st.builds(Delete, st.text(max_size=5), cells),
    st.builds(Fill, st.text(max_size=5), beats, beats, st.lists(cells, max_size=3).map(tuple)),
    st.builds(AddDifficulty, difficulties),
    lightshows,
)


@settings(max_examples=100, deadline=None)
@given(ops)
def test_ops_round_trip_through_json(op):
    assert op_from_dict(json.loads(json.dumps(op.to_dict()))) == op


def test_red_and_blue_parity_breaks_at_same_beats_both_fixed():
    ns = [
        Note(b, x, 0, c, Cut.DOWN) for c, x in ((Color.RED, 1), (Color.BLUE, 2)) for b in (8.0, 8.5)
    ]
    m = bm(ns)
    fs = [f for f in run_checks(m, rules={"parity-break"})]
    assert len(fs) == 2 and len({finding_key(f) for f in fs}) == 2
    assert all(propose(m, f, None, None, 1) is not None for f in fs)


def test_three_note_stack_fixed_by_moves_only():
    ns = [Note(4.0, 0, 0, Color.RED, Cut.DOWN), Note(4.0, 3, 0, Color.RED, Cut.DOWN)]
    m = bm([*ns, Note(4.0, 3, 2, Color.RED, Cut.DOWN)])
    p = propose(m, find(m, "stack-conflict"), None, None, 1)
    assert p is not None and all(isinstance(o, Move) for o in p.ops) and len(p.ops) == 2
    assert len(apply_ops(m, p.ops).difficulties["Expert"].notes) == 3


def test_thinned_difficulty_keeps_bombs_and_walls():
    bomb, wall = Bomb(900.0, 0, 0), Wall(900.0, 0, 0, 1.0, 1, 1)
    m = dense_map(bombs=[bomb], walls=[wall])
    f = next(f for f in run_checks(m) if f.rule == "missing-difficulty" and f.difficulty == "Hard")
    hard = apply_ops(m, propose(m, f, None, None, 1).ops).difficulties["Hard"]
    assert hard.bombs == [bomb] and hard.walls == [wall]
