from collections import Counter

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth import fixer as fx
from saber_tooth.checks import run_checks
from saber_tooth.lightshow.pacing import (
    pace_show,
    strobe_windows,
)
from saber_tooth.model import BasicEvent, BpmEvent
from saber_tooth.timing import Timing
from tests.test_checks_structure import make_map

T120 = Timing(120.0, [])  # 2 beats per second


def strobing(step=0.25, count=40, types=(0, 1, 2, 3, 4), value=1):
    return [BasicEvent(i * step, types[i % len(types)], value) for i in range(count)]


def test_strobe_is_flagged_and_pacing_clears_it():
    ev = strobing()
    assert strobe_windows(ev, {}, T120)
    out, _ = pace_show(ev, {}, T120)
    assert out and strobe_windows(out, {}, T120) == []


def test_calm_show_is_unchanged():
    ev = [BasicEvent(float(b), 0, 1 + (b % 2)) for b in range(0, 40, 2)]
    assert pace_show(ev, {}, T120)[0] == ev


def test_strong_beat_survives_thinning():
    ev = [BasicEvent(3.5, 0, 1), BasicEvent(4.0, 0, 5), BasicEvent(4.25, 0, 1)]
    assert pace_show(ev, {}, T120)[0] == [ev[1]]
    out = pace_show([BasicEvent(7.0, 0, 1), BasicEvent(7.25, 0, 5)], {}, T120, strong_beats=[7.25])
    assert out[0] == [BasicEvent(7.25, 0, 5)]


def test_flash_keeps_its_fade_and_is_never_last():
    ev = [BasicEvent(0.0, 0, 6), BasicEvent(2.0, 0, 7), BasicEvent(4.0, 0, 6)]
    assert pace_show(ev, {}, T120)[0] == ev[:2]
    close = [BasicEvent(0.0, 0, 6), BasicEvent(0.25, 0, 7)]
    assert pace_show(close, {}, T120)[0] == [close[1]]


def test_motion_events_need_one_second():
    ev = [BasicEvent(b, 12, 3) for b in (0.0, 0.5, 1.0, 2.0, 2.5)]
    out, _ = pace_show(ev, {}, T120)
    assert [e.beat for e in out] == [0.0, 2.0]


def test_other_events_and_vfx_groups_pass_through():
    ev = [BasicEvent(0.0, 5, 1), BasicEvent(0.1, 5, 0), BasicEvent(0.2, 14, 1)]
    vfx = {"vfxEventBoxGroups": [{"b": 0.0}, {"b": 0.1}]}
    out, groups = pace_show(ev, vfx, T120)
    assert out == ev and groups == vfx


def test_box_groups_are_paced():
    groups = {
        "lightColorEventBoxGroups": [{"b": i * 0.25, "g": 0, "e": []} for i in range(8)],
        "lightRotationEventBoxGroups": [{"b": i * 0.5, "g": 1, "e": []} for i in range(6)],
    }
    out, kept = pace_show([], groups, T120)
    assert [g["b"] for g in kept["lightColorEventBoxGroups"]] == [0.0, 1.0]
    assert [g["b"] for g in kept["lightRotationEventBoxGroups"]] == [0.0, 2.0]
    assert out == []


def test_tempo_regions_convert_with_map_bpm():
    slow = Timing(60.0, [])  # 1 beat per second: beats 0.5 apart are 0.5 s apart
    ev = [BasicEvent(0.0, 0, 1), BasicEvent(0.5, 0, 5), BasicEvent(1.0, 0, 1)]
    assert pace_show(ev, {}, slow)[0] == ev
    assert len(pace_show(ev, {}, T120)[0]) == 2
    regions = Timing(120.0, [BpmEvent(2.0, 60.0)])
    assert strobe_windows([BasicEvent(2.0, 0, 1), BasicEvent(2.5, 0, 5)], {}, regions) == []


def test_check_registered_and_fix_resolves_it():
    m = make_map(lit=False)
    d = m.difficulties["Expert"]
    d.events = strobing() + [BasicEvent(10.0, t, 0) for t in range(5)]
    found = [f for f in run_checks(m) if f.rule == "light-strobe"]
    assert found and {f.difficulty for f in found} == {"Expert"}
    p = fx.propose(m, found[0], None, None, 1)
    assert p is not None
    fixed = fx.apply_ops(m, p.ops)
    assert not [f for f in run_checks(fixed) if f.rule == "light-strobe"]
    assert fixed.difficulties["Expert"].events and len(d.events) == 45


events = st.builds(
    BasicEvent,
    st.floats(0, 120, allow_nan=False).map(lambda b: round(b, 3)),
    st.sampled_from([0, 1, 2, 3, 4, 5, 8, 9, 12, 13, 14]),
    st.integers(0, 12),
)
box = st.builds(
    lambda b, g: {"b": round(b, 3), "g": g, "e": []},
    st.floats(0, 120, allow_nan=False),
    st.integers(0, 3),
)
group_sets = st.fixed_dictionaries(
    {},
    optional={
        k: st.lists(box, max_size=60)
        for k in ("lightColorEventBoxGroups", "lightRotationEventBoxGroups", "vfxEventBoxGroups")
    },
)
timings = st.builds(
    lambda bpm, at, bpm2: Timing(bpm, [BpmEvent(at, bpm2)]),
    st.floats(60, 240),
    st.floats(1, 100),
    st.floats(60, 240),
)


@settings(max_examples=150, deadline=None)
@given(st.lists(events, max_size=150), group_sets, timings, st.booleans())
def test_pacing_output_is_a_subset_and_respects_limits(ev, groups, timing, pin):
    out, kept = pace_show(ev, groups, timing, [8.0, 16.0], 60.0 if pin else None)
    assert not Counter(out) - Counter(ev)
    for k, v in groups.items():
        assert not Counter(map(id, kept[k])) - Counter(map(id, v))
    assert strobe_windows(out, kept, timing) == []
    lanes: dict[int, BasicEvent] = {}
    for e in sorted(out, key=lambda e: e.beat):
        if e.type in (0, 1, 2, 3, 4):
            lanes[e.type] = e
    assert all(e.value % 4 != 2 or e.value == 0 for e in lanes.values())
    assert pace_show(out, kept, timing, [8.0, 16.0], 60.0 if pin else None)[0] == out
