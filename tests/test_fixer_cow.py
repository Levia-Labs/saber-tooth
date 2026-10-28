import copy
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth import fixer as fx
from saber_tooth.fixer import ops as fo
from saber_tooth.mapio.write import FX_KEY
from saber_tooth.model import BasicEvent, Bomb, Color, Cut, Difficulty, Wall
from tests.test_fixer import _n, bm

NOTES = [_n(4 + i, i % 4, i % 3, Color(i % 2)) for i in range(6)]
WALL = Wall(5, 1, 0, 1, 1, 3)
NEW_WALL = Wall(7, 2, 0, 1, 1, 3)


def synth():
    m = bm(list(NOTES), walls=[WALL], bombs=[Bomb(6, 3, 2)], events=[BasicEvent(1, 0, 1)])
    d = m.difficulties["Expert"]
    n0, n2 = NOTES[0], NOTES[2]
    arc = {"b": n0.beat, "x": n0.x, "y": n0.y, "c": 0, "d": 1, "tb": n2.beat, "tx": n2.x}
    d.raw = {"sliders": [dict(arc, ty=n2.y, tc=1)], "burstSliders": [], "other": [{"k": 1}]}
    d.raw[FX_KEY] = {"_fl": [1.0]}
    m.difficulties["Hard"] = Difficulty("Hard", 12, 0, notes=list(NOTES[:3]), events=[])
    m.difficulties["Hard"].raw = {"sliders": [{"b": 1}]}
    return m


def _show(tag):
    groups = {"lightColorEventBoxGroups": [{"b": 1.0, "g": tag}]}
    return fo.ApplyLightshow(
        "EnvB", None, {"Expert": ([BasicEvent(0.5, 1, tag)], [(0.0, 1)], groups)}
    )


def op_strategy():
    note = st.sampled_from(NOTES)
    diff = st.sampled_from(["Expert", "Hard", "Missing"])
    cut = st.sampled_from(list(Cut))
    return st.one_of(
        st.builds(fo.Move, diff, note, st.integers(0, 3), st.integers(0, 2), cut),
        st.builds(fo.Recolor, diff, note),
        st.builds(fo.Flip, diff, note, cut),
        st.builds(fo.Delete, diff, note),
        st.builds(fo.DeleteWall, diff, st.just(WALL)),
        st.builds(
            fo.Fill,
            diff,
            st.just(0.0),
            st.just(20.0),
            st.just((_n(9, 3, 0),)),
            st.sampled_from([(), (NEW_WALL,)]),
            st.sampled_from([(), (WALL,)]),
        ),
        st.builds(fo.AddDifficulty, st.just(Difficulty("Easy", 10, 0, notes=[_n(2, 0, 0)]))),
        st.sampled_from([_show(1), _show(2)]),
    )


def run(m, ops):
    try:
        return fx.apply_ops(m, ops)
    except fo.OpConflict as e:
        return str(e)


@settings(max_examples=300, deadline=None)
@given(st.lists(op_strategy(), max_size=5))
def test_apply_ops_equals_deepcopy_reference_and_leaves_input_alone(ops):
    m = synth()
    snapshot = copy.deepcopy(m)
    got = run(m, ops)
    assert m == snapshot
    assert got == run(copy.deepcopy(m), ops)


FILL = fo.Fill("Expert", 0.0, 20.0, (_n(9, 3, 0),), (NEW_WALL,), (WALL,))
ALL_OPS = [
    fo.Move("Expert", NOTES[0], 3, 2, Cut.UP),
    fo.Recolor("Expert", NOTES[0]),
    fo.Flip("Expert", NOTES[0], Cut.UP),
    fo.Delete("Expert", NOTES[0]),
    fo.DeleteWall("Expert", WALL),
    FILL,
    fo.AddDifficulty(Difficulty("Easy", 10, 0, notes=[_n(2, 0, 0)])),
    _show(1),
]


def _scribble(m, op):
    names = {"Expert", "Hard"} if isinstance(op, fo.ApplyLightshow) else {"Expert"}
    names = {"Easy"} if isinstance(op, fo.AddDifficulty) else names
    for name in names & set(m.difficulties):
        d = m.difficulties[name]
        d.notes.append("x")
        d.walls.append("x")
        d.raw["junk"] = 1
        keys = (
            ("sliders", "burstSliders")
            if isinstance(op, (fo.Move, fo.Recolor, fo.Flip, fo.Delete))
            else ()
        )
        lists = [d.raw[k] for k in keys if k in d.raw]
        if isinstance(op, fo.ApplyLightshow):
            lists += [d.events, d.boosts, d.raw["lightColorEventBoxGroups"]]
            m.info.environment = "mutated"
        for v in lists:
            v.append("x")


@pytest.mark.parametrize("op", ALL_OPS, ids=lambda o: o.KIND)
def test_mutating_the_output_never_reaches_the_input(op):
    m = synth()
    snapshot = copy.deepcopy(m)
    out = fx.apply_ops(m, [op])
    _scribble(out, op)
    assert m == snapshot


def test_untouched_parts_stay_shared():
    m = synth()
    out = fx.apply_ops(m, [ALL_OPS[3]])
    assert out.difficulties["Hard"] is m.difficulties["Hard"] and out.info is m.info
    assert out.difficulties["Expert"].events is m.difficulties["Expert"].events
    assert out.difficulties["Expert"].raw["other"] is m.difficulties["Expert"].raw["other"]


def test_notes_only_op_is_much_faster_than_deepcopy_on_a_big_event_list():
    m = synth()
    m.difficulties["Expert"].events = [BasicEvent(i / 8, i % 8, 1) for i in range(50_000)]
    ops = [fo.Delete("Expert", NOTES[1])]
    t0 = time.perf_counter()
    for _ in range(3):
        copy.deepcopy(m)
    slow = time.perf_counter() - t0
    t0 = time.perf_counter()
    for _ in range(3):
        fx.apply_ops(m, ops)
    fast = time.perf_counter() - t0
    assert fast * 20 < slow
