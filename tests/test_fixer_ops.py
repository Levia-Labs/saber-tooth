import copy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth import fixer as fx
from saber_tooth.checks import run_checks
from saber_tooth.fixer import ops as fo
from saber_tooth.fixer.verify import _target_remains
from saber_tooth.mapio.write import FX_KEY
from saber_tooth.model import BasicEvent, Bomb, Color, Cut, Difficulty, Note
from tests.test_fixer import FLOW, _n, bm, dense_map, find, missing

HEAD = _n(8, 0, 0)
SLIDER = {"b": 8, "x": 0, "y": 0, "c": 0, "d": 1, "tb": 9, "tx": 2, "ty": 1, "tc": 1, "m": 1}
CHAIN = {"b": 8, "x": 0, "y": 0, "c": 0, "d": 1, "tb": 9, "tx": 1, "ty": 0, "sc": 3, "s": 1}


def arc_map():
    m = bm([HEAD, _n(9, 2, 1)])
    m.difficulties["Expert"].raw = {"sliders": [dict(SLIDER)], "burstSliders": [dict(CHAIN)]}
    return m


def raw(m, key="sliders"):
    return m.difficulties["Expert"].raw[key]


def test_delete_drops_arcs_and_chains_that_reference_the_note():
    m = fx.apply_ops(arc_map(), [fo.Delete("Expert", HEAD)])
    assert raw(m) == [] and raw(m, "burstSliders") == []
    tail = fx.apply_ops(arc_map(), [fo.Delete("Expert", _n(9, 2, 1))])
    assert raw(tail) == [] and len(raw(tail, "burstSliders")) == 1


def test_move_and_flip_retarget_arc_ends():
    m = fx.apply_ops(arc_map(), [fo.Move("Expert", HEAD, 1, 2, Cut.LEFT)])
    head = raw(m)[0]
    assert (head["x"], head["y"], head["d"]) == (1, 2, int(Cut.LEFT)) and (
        head["tx"],
        head["tc"],
    ) == (2, 1)
    tail = fx.apply_ops(arc_map(), [fo.Move("Expert", _n(9, 2, 1), 3, 0, Cut.UP)])
    assert (raw(tail)[0]["tx"], raw(tail)[0]["ty"], raw(tail)[0]["tc"]) == (3, 0, int(Cut.UP))
    flipped = fx.apply_ops(arc_map(), [fo.Flip("Expert", HEAD, Cut.UP)])
    assert raw(flipped)[0]["d"] == int(Cut.UP) and raw(flipped, "burstSliders")[0]["d"] == 0


def test_recolor_drops_arcs_that_would_join_two_hands():
    m = fx.apply_ops(arc_map(), [fo.Recolor("Expert", HEAD)])
    assert raw(m) == [] and raw(m, "burstSliders") == []


def test_unrelated_arcs_and_the_input_map_are_untouched():
    src = arc_map()
    before = copy.deepcopy(src.difficulties["Expert"].raw)
    fx.apply_ops(src, [fo.Delete("Expert", HEAD)])
    assert src.difficulties["Expert"].raw == before


@pytest.mark.parametrize(
    "op",
    [
        fo.Delete("Expert", _n(4, 1, 0)),
        fo.Move("Expert", _n(4, 1, 0), 2, 2, Cut.UP),
        fo.Recolor("Expert", _n(4, 1, 0)),
        fo.Flip("Expert", _n(4, 1, 0), Cut.UP),
        fo.Fill("Expert", 5, 6, (_n(5.5, 3, 0, Color.BLUE),)),
    ],
)
def test_apply_ops_does_not_mutate_its_input(op):
    m = bm([_n(4, 1, 0), _n(7, 2, 0, Color.BLUE)])
    snapshot = copy.deepcopy(m)
    out = fx.apply_ops(m, [op])
    assert m == snapshot and out != snapshot


def test_vision_block_moves_the_centre_note_off_the_centre():
    notes = [_n(8, 1, 1), _n(8.15, 3, 1, Color.BLUE)]
    m = bm(notes)
    p = fx.propose(m, find(m, "vision-block"), None, None, 1)
    assert isinstance(p.ops[0], fo.Move) and p.ops[0].note == notes[0]
    assert not (p.ops[0].x in (1, 2) and p.ops[0].y == 1)


note_strategy = st.builds(
    Note,
    beat=st.integers(8, 200).map(lambda i: i / 4),
    x=st.integers(0, 3),
    y=st.integers(0, 2),
    color=st.sampled_from(Color),
    cut=st.sampled_from([c for c in Cut if c != Cut.ANY]),
)


@settings(max_examples=60, deadline=None)
@given(st.lists(note_strategy, min_size=2, max_size=30))
def test_fix_removes_the_target_finding_and_adds_none(ns):
    m = bm(ns)
    before = run_checks(m, rules=FLOW)
    for f in before:
        p = fx.propose(m, f, None, None, 1)
        if p is None:
            continue
        after = run_checks(fx.apply_ops(m, p.ops), rules=FLOW)
        assert not fx.new_findings(after, before)
        assert not _target_remains(f, before, after)


def test_thinned_difficulty_drops_bombs_sharing_a_kept_notes_cell():
    m = dense_map()
    hard = fx.apply_ops(m, fx.propose(m, missing(m, "Hard"), None, None, 1).ops)
    kept = hard.difficulties["Hard"].notes[0]
    on_note, apart = Bomb(kept.beat, kept.x, kept.y), Bomb(900.0, 0, 0)
    m2 = dense_map(bombs=[on_note, apart])
    out = fx.apply_ops(m2, fx.propose(m2, missing(m2, "Hard"), None, None, 1).ops)
    assert out.difficulties["Hard"].bombs == [apart]


def _show(tag):
    groups = {"lightColorEventBoxGroups": [{"b": 1.0, "g": tag}]}
    return fo.ApplyLightshow(
        "EnvA", None, {"Expert": ([BasicEvent(0.5, 1, tag)], [(0.0, True)], groups)}
    )


@pytest.mark.parametrize("show_first", [True, False])
def test_lightshow_reaches_a_difficulty_added_in_the_same_apply(show_first):
    m = bm([_n(4, 1, 0)])
    add = fo.AddDifficulty(Difficulty("Hard", 12, 0, notes=[_n(4, 1, 0)]))
    ops = [_show(3), add] if show_first else [add, _show(3)]
    out = fx.apply_ops(m, ops)
    for name in ("Expert", "Hard"):
        d = out.difficulties[name]
        assert d.events == [BasicEvent(0.5, 1, 3)] and d.boosts == [(0.0, True)]
        assert d.raw["lightColorEventBoxGroups"] == [{"b": 1.0, "g": 3}]


def test_lightshow_replaces_the_fx_collection_with_the_group_set():
    m = bm([_n(4, 1, 0)])
    m.difficulties["Expert"].raw[FX_KEY] = {"_fl": [1.0], "_il": []}
    assert FX_KEY not in fx.apply_ops(m, [_show(1)]).difficulties["Expert"].raw
