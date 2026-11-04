import contextlib
import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.analysis import Analysis
from saber_tooth.environments import BY_NAME, COLOR_ROLES
from saber_tooth.style import Style, parse_style, pick_environment, resolve_style, to_scheme

HEX = st.from_regex(r"#[0-9a-fA-F]{6}", fullmatch=True)
COLORS = st.dictionaries(st.sampled_from(sorted(COLOR_ROLES)), HEX)
ANYTHING = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda c: st.lists(c) | st.dictionaries(st.text(), c),
)


def song(bpm, density, hh_share, seconds=60):
    spb = 60.0 / bpm
    beats = [i * spb for i in range(int(seconds / spb))]
    n = int(density * seconds)
    hh_n = int(n * hh_share)
    kick = [i * seconds / max(1, n - hh_n) for i in range(max(0, (n - hh_n) // 2))]
    snare = [t + 0.1 for t in kick]
    hh = [i * seconds / max(1, hh_n) for i in range(hh_n)]
    return Analysis("s", "A", bpm, beats, kick, snare, hh, None)


@given(st.sampled_from(sorted(BY_NAME)), COLORS)
def test_valid_styles_round_trip(env, colors):
    style = parse_style({"environment": env, "colors": colors})
    assert style == Style(env, {k: v.lower() for k, v in colors.items()})
    assert parse_style(json.loads(json.dumps(style.to_dict()))) == style


@given(ANYTHING)
def test_parse_style_never_raises_anything_but_value_error(raw):
    with contextlib.suppress(ValueError):
        parse_style(raw)


@given(st.text(max_size=12).filter(lambda t: not (len(t) == 7 and t[0] == "#")))
def test_bad_colour_text_is_refused(text):
    with pytest.raises(ValueError):
        parse_style({"colors": {"saber_left": text}})


@pytest.mark.parametrize(
    "raw",
    [
        {"environment": "DefaultEnvironment"},
        {"environment": "../x"},
        {"colors": {"sky": "#ffffff"}},
        {"colors": {"obstacle": "#fff"}},
        {"colors": []},
        {"extra": 1},
        "NiceEnvironment",
    ],
)
def test_bad_styles_are_refused(raw):
    with pytest.raises(ValueError):
        parse_style(raw)


def test_known_environments_limit_the_choice():
    with pytest.raises(ValueError):
        parse_style({"environment": "NiceEnvironment"}, {"WeaveEnvironment"})


def test_empty_style_is_none():
    assert parse_style(None) is None
    assert parse_style({}) is None
    assert parse_style({"colors": {}}) is None


def test_scheme_overlays_style_colours_on_the_palette():
    env = BY_NAME["WeaveEnvironment"]
    scheme = to_scheme(env, Style(None, {"saber_left": "#ff0000"}))
    assert scheme.colors["saberAColor"] == {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}
    assert set(scheme.colors) == set(COLOR_ROLES.values())
    assert scheme.id == "st-WeaveEnvironment"


def test_style_environment_wins_over_the_song():
    env, scheme = resolve_style(Style("WeaveEnvironment", {}), song(190, 8, 0.1), 1)
    assert env.name == "WeaveEnvironment" and scheme.colors["saberBColor"]


def test_song_features_move_the_choice():
    calm = {pick_environment(song(70, 0.8, 0.6), s).name for s in range(30)}
    wild = {pick_environment(song(190, 8, 0.1), s).name for s in range(30)}
    assert calm.isdisjoint(wild)
    assert len(calm | wild) >= 4


def test_pick_is_seeded_and_limited_to_names():
    a = song(120, 3, 0.4)
    assert pick_environment(a, 5) == pick_environment(a, 5)
    only = {pick_environment(a, s, {"OriginsEnvironment"}).name for s in range(10)}
    assert only == {"OriginsEnvironment"}
    assert pick_environment(a, 0, {"Unknown"}).name in BY_NAME
