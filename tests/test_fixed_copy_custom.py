"""A fixed copy keeps vanilla-safe Info customData and exactly the files that data references."""

import json
import shutil

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from saber_tooth.map_folder_guard import check_map_folder, named_refs
from saber_tooth.mapio import find_info, load_map
from saber_tooth.service.writeout import replace_fixed, write_fixed
from tests.test_service import FIXTURE

STANDARD = {"info.dat", "hard.dat", "expertplus.dat", "bpminfo.dat"}
_FILE = st.sampled_from(["a.png", "b.PNG", "c.jpg", "mod.vivify", "v.mp4", "x.txt", "song.ogg"])
fresh = settings(
    max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def _original(tmp_path, custom, files, tag="o"):
    folder = tmp_path / f"{tag}-src"
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(FIXTURE, folder)
    info_path = find_info(folder)
    info = json.loads(info_path.read_text(encoding="utf-8"))
    info["_customData"] = custom
    info_path.write_text(json.dumps(info), encoding="utf-8")
    for name in files:
        (folder / name).write_bytes(b"x")
    return folder


def _copy(tmp_path, original, tag="o"):
    levels = tmp_path / f"{tag}-levels"
    if levels.exists():
        shutil.rmtree(levels)
    levels.mkdir()
    return write_fixed(levels, original, load_map(original), "Out [saber-tooth]")


def _written_info(copy):
    return json.loads(find_info(copy).read_text(encoding="utf-8"))


def test_contributors_and_icons_survive_and_mod_files_go(tmp_path):
    custom = {
        "_contributors": [{"_role": "Mapper", "_name": "Z", "_iconPath": "icon.png"}],
        "_editors": {"_lastEditedBy": "MM", "MM": {"version": "1.0"}},
        "_environmentRemoval": ["Spectrograms"],
        "_requirements": ["Chroma"],
    }
    original = _original(tmp_path, custom, ["icon.png", "cinema-video.json", "fx.vivify"])
    copy = _copy(tmp_path, original)
    data = _written_info(copy)["_customData"]
    assert data["_contributors"] == custom["_contributors"]
    assert data["_editors"] == custom["_editors"]
    assert "_environmentRemoval" not in data and "_requirements" not in data
    names = {p.name for p in copy.iterdir()}
    assert "icon.png" in names and {"song.ogg", "cover.jpg"} <= names
    assert "cinema-video.json" not in names and "fx.vivify" not in names
    assert check_map_folder(copy, copy.parent) == []


def test_no_custom_data_key_when_nothing_is_kept(tmp_path):
    copy = _copy(tmp_path, _original(tmp_path, {"_requirements": ["Noodle Extensions"]}, []))
    assert "_customData" not in _written_info(copy)


def test_v4_style_keys_are_kept(tmp_path):
    custom = {"contributors": [{"role": "Mapper", "iconPath": "i.png"}], "editors": {}}
    copy = _copy(tmp_path, _original(tmp_path, custom, ["i.png"]))
    assert (copy / "i.png").is_file()


def test_bpminfo_dat_survives_and_tempo_round_trips(tmp_path):
    original = _original(tmp_path, {}, [])
    spans = [(0, 44100, 0, 2), (44100, 88200, 2, 5)]  # 120 bpm, then 180 bpm
    regions = [
        {"_startSampleIndex": a, "_endSampleIndex": b, "_startBeat": c, "_endBeat": e}
        for a, b, c, e in spans
    ]
    body = {"_songFrequency": 44100, "_regions": regions}
    (original / "BPMInfo.dat").write_text(json.dumps(body), encoding="utf-8")
    copy = _copy(tmp_path, original)
    assert (copy / "BPMInfo.dat").is_file()
    before, after = load_map(original), load_map(copy)
    for name, diff in before.difficulties.items():
        assert after.difficulties[name].bpm_events == diff.bpm_events


def test_replace_fixed_applies_the_same_rule(tmp_path):
    original = _original(tmp_path, {"_contributors": [{"_iconPath": "i.png"}]}, ["i.png", "z.png"])
    levels = tmp_path / "rl"
    levels.mkdir()
    out = replace_fixed(levels, original, load_map(original), "Out [saber-tooth]")
    names = {p.name for p in out.iterdir()}
    assert "i.png" in names and "z.png" not in names


@given(
    icons=st.lists(_FILE, max_size=4),
    dropped=st.lists(_FILE, max_size=4),
    extra=st.lists(_FILE, max_size=4),
)
@fresh
def test_every_file_is_referenced_or_standard_and_every_reference_exists(
    tmp_path, icons, dropped, extra
):
    custom = {
        "_contributors": [{"_name": "n", "_iconPath": i} for i in icons],
        "_environmentRemoval": list(dropped),
        "_customEnvironment": {"files": list(dropped)},
    }
    original = _original(tmp_path, custom, [*icons, *dropped, *extra, "cinema-video.json"], "p")
    copy = _copy(tmp_path, original, "p")
    info = _written_info(copy)
    refs = named_refs(info)
    present = {p.name.lower() for p in copy.iterdir()}
    original_names = {p.name.lower() for p in original.iterdir()}
    assert all(n in refs or n in STANDARD for n in present)
    assert all(r in present for r in refs if r in original_names)
    assert all(n.lower() in present for n in (info["_songFilename"], info["_coverImageFilename"]))
