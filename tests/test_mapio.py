from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.mapio import MapParseError, find_info, load_map, write_map
from saber_tooth.model import Color, Cut, Note

FIX = Path(__file__).parent / "fixtures" / "maps"


def test_discovers_mixed_case_names():
    m = load_map(FIX / "v2_basic")
    assert find_info(FIX / "v2_basic").name == "info.dat"
    assert set(m.difficulties) == {"Hard", "ExpertPlus"}


def test_v2_conversions():
    d = load_map(FIX / "v2_basic").difficulties["Hard"]
    assert len(d.notes) == 2 and len(d.bombs) == 1
    assert (d.walls[0].y, d.walls[0].height) == (2, 3)
    assert d.boosts == [(8.0, True)]


def test_v3_box_groups_preserved():
    m = load_map(FIX / "v3_boxes")
    assert len(m.difficulties["Expert"].raw["lightColorEventBoxGroups"]) == 1
    assert m.info.color_scheme and m.info.color_scheme.id == "Custom"


def test_v4_notes_resolved():
    m = load_map(FIX / "v4_split")
    n = m.difficulties["Easy"].notes[0]
    assert (n.x, n.y, n.color) == (1, 0, Color.RED)
    assert m.difficulties["Easy"].events  # lightshow file merged
    assert m.info.color_scheme.colors["saberAColor"]["r"] == 1.0


def test_v2_bpm_changes_loaded():
    d = load_map(FIX / "v2_bpm").difficulties["Expert"]
    assert d.bpm_events and d.bpm_events[0].bpm == 60.0


def test_broken_json_raises(tmp_path):
    (tmp_path / "Info.dat").write_text("{", encoding="utf-8")
    with pytest.raises(MapParseError):
        load_map(tmp_path)


def test_writer_emits_no_custom_data(tmp_path):
    m = load_map(FIX / "v2_basic")
    write_map(m, tmp_path / "out", copy_from=FIX / "v2_basic")
    text = (tmp_path / "out" / "Info.dat").read_text(encoding="utf-8")
    assert "_customData" not in text and "_requirements" not in text
    assert (tmp_path / "out" / "song.ogg").is_file()


def test_v3_round_trip_keeps_boxes(tmp_path):
    m = load_map(FIX / "v3_boxes")
    write_map(m, tmp_path / "o", copy_from=FIX / "v3_boxes")
    again = load_map(tmp_path / "o")
    assert again.difficulties["Expert"].raw == m.difficulties["Expert"].raw
    assert again.info.color_scheme == m.info.color_scheme


notes = st.builds(
    Note,
    beat=st.integers(0, 4000).map(lambda i: i / 8),
    x=st.integers(0, 3),
    y=st.integers(0, 2),
    color=st.sampled_from(Color),
    cut=st.sampled_from(Cut),
    angle=st.just(0),
)


@settings(max_examples=50)
@given(st.lists(notes, max_size=60))
def test_round_trip(tmp_path_factory, ns):
    base = load_map(FIX / "v2_basic")
    base.difficulties["Hard"].notes = sorted(ns)
    out = tmp_path_factory.mktemp("rt") / "m"
    write_map(base, out, copy_from=FIX / "v2_basic")
    assert load_map(out).difficulties["Hard"].notes == sorted(ns)


def _copy_fixture(name: str, dest: Path) -> Path:
    import shutil

    shutil.copytree(FIX / name, dest)
    return dest


def test_info_filename_traversal_rejected(tmp_path):
    m = _copy_fixture("v2_basic", tmp_path / "a")
    info = m / "info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace("song.ogg", "../x.egg"), encoding="utf-8"
    )
    with pytest.raises(MapParseError):
        load_map(m)


def test_difficulty_filename_traversal_rejected(tmp_path):
    m = _copy_fixture("v2_basic", tmp_path / "a")
    info = m / "info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace("hard.dat", "..\\x.dat"), encoding="utf-8"
    )
    with pytest.raises(MapParseError):
        load_map(m)


def test_write_strips_nested_custom_data(tmp_path):
    import json

    m = _copy_fixture("v3_boxes", tmp_path / "a")
    exp = m / "Expert.dat"
    data = json.loads(exp.read_text(encoding="utf-8"))
    data["sliders"] = [{"b": 1, "customData": {"x": 1}, "n": [{"_customData": {"y": 2}, "k": 3}]}]
    data["lightColorEventBoxGroups"][0]["customData"] = {"z": 1}
    exp.write_text(json.dumps(data), encoding="utf-8")
    write_map(load_map(m), tmp_path / "o", copy_from=m)
    text = (tmp_path / "o" / "Expert.dat").read_text(encoding="utf-8")
    assert "ustomData" not in text and '"k":3' in text


def test_v2_bpm_event_without_float_skipped_and_deduped(tmp_path):
    import json

    m = _copy_fixture("v2_bpm", tmp_path / "a")
    exp = m / "Expert.dat"
    data = json.loads(exp.read_text(encoding="utf-8"))
    data["_events"] = [
        {"_time": 0, "_type": 100, "_value": 0, "_floatValue": 60},
        {"_time": 8, "_type": 100, "_value": 0},
    ]
    exp.write_text(json.dumps(data), encoding="utf-8")
    bpms = load_map(m).difficulties["Expert"].bpm_events
    assert [(b.beat, b.bpm) for b in bpms] == [(0.0, 60.0)]


def _edit(folder: Path, name: str, fn) -> None:
    import json

    p = folder / name
    data = json.loads(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(json.dumps(data), encoding="utf-8")


def test_null_colour_scheme_entry_is_a_parse_error(tmp_path):
    m = _copy_fixture("v2_basic", tmp_path / "a")
    _edit(m, "info.dat", lambda d: d.update(_colorSchemes=[None]))
    _edit(
        m,
        "info.dat",
        lambda d: d["_difficultyBeatmapSets"][0]["_difficultyBeatmaps"][0].update(
            _beatmapColorSchemeIdx=0
        ),
    )
    with pytest.raises(MapParseError):
        load_map(m)


@pytest.mark.parametrize("bad", [0, -60, 1e999])
def test_bad_bpm_event_is_a_parse_error(tmp_path, bad):
    m = _copy_fixture("v3_boxes", tmp_path / "a")
    _edit(m, "Expert.dat", lambda d: d.update(bpmEvents=[{"b": 4, "m": bad}]))
    with pytest.raises(MapParseError):
        load_map(m)


@pytest.mark.parametrize("field", [("x", 4), ("x", -1), ("y", 3), ("d", 9), ("d", 1000)])
def test_mapping_extensions_notes_rejected(tmp_path, field):
    m = _copy_fixture("v3_boxes", tmp_path / "a")
    _edit(m, "Expert.dat", lambda d: d["colorNotes"][0].update({field[0]: field[1]}))
    with pytest.raises(MapParseError, match="Mapping Extensions"):
        load_map(m)


def test_fx_events_collection_round_trips(tmp_path):
    m = _copy_fixture("v3_boxes", tmp_path / "a")
    fx = {"_fl": [0.5], "_il": [3]}
    _edit(
        m,
        "Expert.dat",
        lambda d: d.update(_fxEventsCollection=fx, vfxEventBoxGroups=[{"b": 1, "g": 0, "e": []}]),
    )
    write_map(load_map(m), tmp_path / "o", copy_from=m)
    out = load_map(tmp_path / "o").difficulties["Expert"]
    assert out.raw["_fxEventsCollection"] == fx and out.raw["vfxEventBoxGroups"]
    import json

    text = json.loads((tmp_path / "o" / "Expert.dat").read_text(encoding="utf-8"))
    assert text["_fxEventsCollection"] == fx
