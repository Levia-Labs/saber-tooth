from pathlib import Path

import pytest

from saber_tooth.lightshow import Templates, Unit, bar_energy, build_lightshow, learn
from saber_tooth.lightshow.apply import choose_environment
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
    assert events == sorted(events) and boosts == sorted(boosts)
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


def test_learned_templates_apply():
    t = learn(FIX)
    bm = _beatmap(8, range(2, 6))
    p = build_lightshow(bm, Timing(120, []), t, None, 2)
    assert p.environment in t.units and p.events["Expert"][0]
