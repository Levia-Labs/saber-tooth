from pathlib import Path

import pytest

from saber_tooth.analysis import Analysis
from saber_tooth.lightshow import Templates, Unit, bar_energy, build_lightshow, learn
from saber_tooth.lightshow.apply import _sections, choose_environment
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import (
    BasicEvent,
    Beatmap,
    Color,
    ColorScheme,
    Cut,
    Difficulty,
    MapInfo,
    Note,
)
from saber_tooth.timing import Timing

FIX = Path(__file__).parent / "fixtures" / "maps"
ENERGIES = (0.1, 0.2, 0.45, 0.6, 0.9, 1.0)


def _beatmap(bars: int = 40, loud: range = range(12, 20)) -> Beatmap:
    notes = []
    for bar in range(bars):
        for k in range(16 if bar in loud else 1):
            notes.append(Note(bar * 4 + k * 0.25, 0, 0, Color.RED, Cut.ANY))
    d = Difficulty("Expert", 16, 0, notes=notes)
    info = MapInfo("s", "", "a", "m", 120, "s.ogg", "c.jpg", 0, 10, "BTSEnvironment")
    return Beatmap(info, {"Expert": d, "Hard": Difficulty("Hard", 16, 0, notes=notes[::2])})


def _templates() -> Templates:
    def unit(env: str, src: str, e: float) -> Unit:
        group = {"b": 1.0, "g": 0, "e": [{"b": 0.0}]}
        return Unit(
            env,
            src,
            e,
            [BasicEvent(0.5, 1, int(e * 10))],
            [(0.0, True)],
            {"lightColorEventBoxGroups": [group]},
        )

    units = {
        env: [unit(env, src, e) for src in ("a", "b") for e in ENERGIES] for env in ("EnvA", "EnvB")
    }
    return Templates(units, {"EnvA": [ColorScheme("S", {})]})


def _show(**kw):
    bm = _beatmap()
    return bm, build_lightshow(bm, Timing(120, []), _templates(), None, kw.pop("seed", 1), **kw)


def test_sorted_and_within_bounds():
    bm, p = _show()
    last = max(n.beat for d in bm.difficulties.values() for n in d.notes)
    assert set(p.events) == {"Expert", "Hard"}
    events, boosts, groups = p.events["Expert"]
    assert [e.beat for e in events] == sorted(e.beat for e in events)
    assert boosts == sorted(boosts)
    assert all(0 <= e.beat <= last + 4 for e in events)
    assert all(0 <= b <= last + 4 for b, _ in boosts)
    g = groups["lightColorEventBoxGroups"]
    assert [x["b"] for x in g] == sorted(x["b"] for x in g)
    assert all(0 <= x["b"] <= last + 4 for x in g)
    assert p.events["Hard"] == p.events["Expert"]
    off = [e for e in events if e.beat == last + 2]
    assert {e.type for e in off} == {0, 1, 2, 3, 4} and all(e.value == 0 for e in off)
    assert not [e for e in events if e.beat > last + 2]


def test_high_energy_section_has_boost_on_and_low_has_off():
    _, p = _show()
    boosts = p.events["Expert"][1]
    assert any(on and 48 <= b < 80 for b, on in boosts)
    assert any(not on and b < 48 for b, on in boosts)


def test_environment_learned_and_scheme():
    t = _templates()
    _, p = _show()
    assert p.environment in t.units
    assert (p.color_scheme is not None) == (p.environment == "EnvA")
    _, q = _show(environment="EnvB")
    assert q.environment == "EnvB" and q.color_scheme is None
    assert choose_environment(t, 3) in t.units


def test_quiet_bars_use_low_energy_units():
    _, p = _show()
    quiet = [e for e in p.events["Expert"][0] if e.beat < 48 and e.value]
    assert quiet and all(e.value < 5 for e in quiet)
    fade = [e for e in p.events["Expert"][0] if e.beat >= 156 and e.value]
    assert fade and all(e.value < 3 for e in fade)


def test_deterministic_and_templates_untouched():
    t = _templates()
    bm = _beatmap()
    a = build_lightshow(bm, Timing(120, []), t, None, 7)
    b = build_lightshow(bm, Timing(120, []), t, None, 7)
    assert a == b
    assert t.units["EnvA"][0].groups["lightColorEventBoxGroups"][0]["b"] == 1.0
    a.events["Expert"][2]["lightColorEventBoxGroups"][0]["e"].append(1)
    assert t.units["EnvA"][0].groups["lightColorEventBoxGroups"][0]["e"] == [{"b": 0.0}]


def test_empty_templates_raise():
    with pytest.raises(ValueError, match="run learn first"):
        build_lightshow(_beatmap(), Timing(120, []), Templates(), None, 1)


def test_bar_energy_density_normalised():
    e = bar_energy(_beatmap(), Timing(120, []), None)
    assert len(e) == 40 and max(e) == 1.0 and e[0] < 0.2 and e[13] == 1.0


def _counts_map(counts: list[int]) -> Beatmap:
    notes = [
        Note(bar * 4 + k * 0.25, 0, 0, Color.RED, Cut.ANY)
        for bar, n in enumerate(counts)
        for k in range(n)
    ]
    info = MapInfo("s", "", "a", "m", 120, "s.ogg", "c.jpg", 0, 10, "BTSEnvironment")
    return Beatmap(info, {"Expert": Difficulty("Expert", 16, 0, notes=notes)})


def _marked_templates() -> Templates:
    def unit(src: str, e: float) -> Unit:
        group = {"b": 1.0, "g": ord(src), "e": []}
        return Unit("EnvA", src, e, [BasicEvent(0.5, 1, int(e * 10))], [], {BOX_KEYS[0]: [group]})

    units = [unit("a", e) for e in ENERGIES] + [unit("b", e) for e in ENERGIES]
    units += [unit("x", 0.9), unit("x", 1.0)]
    return Templates({"EnvA": units}, {})


def _bar_values(p, bars: int) -> dict[int, int]:
    return {int(e.beat // 4): e.value for e in p.events["Expert"][0] if e.type == 1 and e.value}


def test_bar_energy_follows_analysis_onsets():
    bm = _counts_map([4] * 12)
    kick = [10 + k * 0.25 for k in range(32)]
    a = Analysis("n", "k", 120, [], kick, [], [], None)
    e = bar_energy(bm, Timing(120, []), a)
    assert e[5:9] == [1.0] * 4 and e[:5] == [0.0] * 5 and e[9:] == [0.0] * 3


def test_bar_energy_mostly_silent_uses_max():
    e = bar_energy(_counts_map([0] * 19 + [3]), Timing(120, []), None)
    assert e[-1] == 1.0 and sum(e) == 1.0
    assert bar_energy(_counts_map([0, 0]), Timing(120, []), None) == [0.0]


def test_section_boundary_threshold():
    assert _sections([0.5] * 4 + [0.74] * 4) == [(0, 8)]
    assert _sections([0.5] * 4 + [0.76] * 4) == [(0, 4), (4, 8)]


def test_trailing_partial_block_merges():
    assert _sections([0.5] * 40 + [0.0]) == [(0, 41)]
    assert _sections([0.1, 0.9]) == [(0, 2)]


def test_donor_consistent_within_section():
    bm = _counts_map([1] * 12 + [16] * 8 + [1] * 20)
    p = build_lightshow(bm, Timing(120, []), _marked_templates(), None, 5)
    groups = p.events["Expert"][2][BOX_KEYS[0]]
    for lo, hi in ((0, 12), (12, 20), (20, 38)):
        donors = {g["g"] for g in groups if lo * 4 <= g["b"] < hi * 4}
        assert len(donors) == 1


def test_quiet_section_donor_has_low_units():
    t = _marked_templates()
    t.units["EnvA"] = [u for u in t.units["EnvA"] if u.source != "a" or u.energy < 0.5]
    t.units["EnvA"] = [u for u in t.units["EnvA"] if u.source == "x" or u.source == "a"]
    p = build_lightshow(_counts_map([1] * 12 + [16] * 8 + [1] * 20), Timing(120, []), t, None, 3)
    quiet = [g for g in p.events["Expert"][2][BOX_KEYS[0]] if g["b"] < 48]
    assert quiet and {g["g"] for g in quiet} == {ord("a")}
    ev = [e for e in p.events["Expert"][0] if e.beat < 48 and e.value]
    assert all(e.value < 5 for e in ev)


def test_motif_repeats_every_four_bars():
    counts = [2, 6, 12, 16] * 3 + [16, 16]
    p = build_lightshow(_counts_map(counts), Timing(120, []), _marked_templates(), None, 1)
    vals = _bar_values(p, 14)
    assert all(vals[i] == vals[i + 4] for i in range(8))
    assert len({vals[i] for i in range(4)}) > 1


def test_boost_resets_after_high_section():
    bm = _counts_map([16] * 8 + [9] * 8 + [1] * 8)
    p = build_lightshow(bm, Timing(120, []), _templates(), None, 1)
    boosts = p.events["Expert"][1]
    assert (0.0, True) in boosts and (32.0, False) in boosts


def test_lights_off_sorts_after_unit_events_at_same_beat():
    t = Templates({"E": [Unit("E", "s", 0.1, [BasicEvent(0.0, 0, 5)], [], {})]}, {})
    bm = _counts_map([1, 1])  # last note at beat 4 -> off at 6; unit events at 0 and 4
    t.units["E"][0].events.append(BasicEvent(2.0, 0, 7))  # bar 1 start 4 + 2 == 6
    p = build_lightshow(bm, Timing(120, []), t, None, 1)
    at_off = [e for e in p.events["Expert"][0] if e.beat == 6.0 and e.type == 0]
    assert [e.value for e in at_off] == [7, 0]


def test_learned_templates_apply():
    t = learn(FIX)
    bm = _counts_map([2] * 4 + [12] * 8 + [2] * 4)
    p = build_lightshow(bm, Timing(120, []), t, None, 2)
    events, _, groups = p.events["Expert"]
    env_units = t.units[p.environment]
    allowed = {(e.type, e.value) for u in env_units for e in u.events} | {(i, 0) for i in range(5)}
    assert events and all((e.type, e.value) in allowed for e in events)
    pool = [g["e"] for u in env_units for gs in u.groups.values() for g in gs]
    assert all(g["e"] in pool for gs in groups.values() for g in gs)
    assert p.color_scheme in (*t.schemes.get(p.environment, []), None)
