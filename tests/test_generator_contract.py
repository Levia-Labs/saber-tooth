"""The generator's contract: a generated map has zero findings under every registered rule."""

import itertools

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from saber_tooth.analysis import Analysis
from saber_tooth.assemble import _build
from saber_tooth.checks import MAP_RULES, RULES, run_checks
from saber_tooth.lightshow import Templates, Unit
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import DIFFICULTIES, BasicEvent, ColorScheme
from saber_tooth.songmeta import SongMeta

META = SongMeta("Fixture", "", "Nobody")


def _templates() -> Templates:
    group = {"b": 1.0, "g": 0, "e": [{"b": 0.0}]}
    units = [
        Unit("EnvA", s, e, [BasicEvent(0.5, 1, 1)], [(0.0, True)], {BOX_KEYS[0]: [group]})
        for s in ("a", "b")
        for e in (0.1, 0.5, 0.9)
    ]
    return Templates({"EnvA": units}, {"EnvA": [ColorScheme("S", {})]})


def song(bpms: list[float], seconds: float, density: int = 2, swing: float = 0.0) -> Analysis:
    """Beat grid that moves through `bpms` in equal stretches of the song."""
    beats: list[float] = []
    t = 0.0
    while t < seconds:
        bpm = bpms[min(len(bpms) - 1, int(t / seconds * len(bpms)))]
        beats.append(t)
        t += 60.0 / bpm
    spb = [b - a for a, b in itertools.pairwise(beats)] or [0.5]
    hh = [b + s / 2 * (1 + swing) for b, s in zip(beats, spb, strict=False)]
    step = max(1, round(4 / density))
    return Analysis("s", "A minor", bpms[0], beats, beats[::2], beats[1::2], hh[::step] or hh, None)


def contract(a: Analysis, seed: int, templates: Templates | None):
    bm = _build(a, None, templates, seed, META)  # type: ignore[arg-type]
    assert set(bm.difficulties) == set(DIFFICULTIES)
    assert all(d.notes for d in bm.difficulties.values())
    findings = run_checks(bm, a) + run_checks(bm)  # with the song, and as the survey sees it
    assert findings == [], findings[:3]
    assert bm.info.environment != "DefaultEnvironment"


CASES = {
    "slow": ([72.0], 150, 1, 0.0),
    "mid": ([128.0], 120, 2, 0.1),
    "fast": ([190.0], 90, 4, 0.0),
    "tempo-change": ([100.0, 140.0, 90.0], 150, 2, 0.0),
    "big-change": ([80.0, 170.0], 120, 3, 0.2),
    "dense-hats": ([150.0], 100, 8, 0.3),
}


def test_every_rule_is_exercised():
    assert {"light-strobe", "no-rest", "note-converge", "wall-short"} <= set(RULES) | set(MAP_RULES)


@pytest.mark.parametrize("name", CASES)
def test_fixture_songs_have_zero_findings(name):
    bpms, seconds, density, swing = CASES[name]
    contract(song(bpms, seconds, density, swing), 3, _templates())


@settings(max_examples=12, deadline=None, suppress_health_check=list(HealthCheck))
@given(
    st.lists(st.floats(70, 200), min_size=1, max_size=3),
    st.integers(40, 120),
    st.integers(1, 8),
    st.integers(0, 10_000),
)
def test_seeds_have_zero_findings(bpms, seconds, density, seed):
    contract(song(bpms, seconds, density), seed, _templates())


@settings(max_examples=12, deadline=None, suppress_health_check=list(HealthCheck))
@given(
    st.integers(80, 180),
    st.lists(st.floats(0.0, 100.0), min_size=40, max_size=400),
    st.lists(st.floats(0.0, 100.0), min_size=0, max_size=120),
    st.integers(0, 10_000),
)
def test_irregular_onsets_have_zero_findings(bpm, hats, kicks, seed):
    """Onsets off the grid, bursts and silent stretches, as real analysis produces."""
    spb = 60.0 / bpm
    beats = [i * spb for i in range(int(100 / spb))]
    onsets = sorted(hats)
    a = Analysis("s", "A", bpm, beats, sorted(kicks), beats[1::4], onsets, None)
    contract(a, seed, _templates())
