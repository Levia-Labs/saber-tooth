# ruff: noqa: F811
import json

import pytest

from saber_tooth.crop.errors import CropError, InvalidWindow, NoNotes
from saber_tooth.mapio import load_map
from saber_tooth.service import map_id_for
from tests.crop_helpers import NAME, cuts, make_360, make_service  # noqa: F401
from tests.test_service import _hashes

MID = map_id_for(NAME)


def test_timeline_of_an_unscanned_map_is_map_only(tmp_path):
    svc = make_service(tmp_path)
    tl = svc.crop_timeline(MID)
    assert tl["map_id"] == MID and tl["map_only"] is True and tl["grid_drift_s"] is None
    assert set(tl["lengths"]) == {"60", "120"} and tl["hardest"] == "ExpertPlus"
    assert tl["lengths"]["60"]["enabled"] and tl["lengths"]["120"]["enabled"]
    json.dumps(tl)


def test_a_scanned_map_uses_its_stored_analysis(tmp_path):
    svc = make_service(tmp_path)
    project = svc.uploads / "proj"
    project.mkdir(parents=True)
    (project / "meta.json").write_text(
        json.dumps({"name": "proj", "key": "C", "bpm": 120}), encoding="utf-8"
    )
    grid = "".join(f"{i * 0.5},1\n" for i in range(300))
    (project / "beats.csv").write_text(grid, encoding="utf-8")
    (project / "kick.csv").write_text(grid, encoding="utf-8")
    svc.store.replace_open_proposals(MID, [], {"findings": [], "analysis": "proj"})
    tl = svc.crop_timeline(MID)
    assert tl["map_only"] is False
    assert tl["grid_drift_s"] == pytest.approx(0.0)


def test_crop_map_writes_a_folder_and_leaves_the_original(tmp_path, cuts):
    svc = make_service(tmp_path)
    original = svc.levels / NAME
    before = _hashes(original)
    window = svc.crop_timeline(MID)["lengths"]["60"]["suggestions"][0]
    result = svc.crop_map(MID, window["start_beat"], window["end_beat"])
    assert result["folder"] == "Song [1 min]" and result["label"] == "1 min"
    assert result["cropped_id"] == map_id_for("Song [1 min]")
    assert result["length_s"] == pytest.approx(window["length_s"])
    assert _hashes(original) == before
    written = load_map(svc.levels / result["folder"])
    assert len(written.difficulties) == 5 and len(cuts) == 1
    assert any(m["folder"] == "Song [1 min]" for m in svc.store.list_maps())


def test_a_two_minute_window_is_labelled_two_minutes(tmp_path, cuts):
    svc = make_service(tmp_path)
    window = svc.crop_timeline(MID)["lengths"]["120"]["suggestions"][0]
    assert svc.crop_map(MID, window["start_beat"], window["end_beat"])["label"] == "2 min"


def test_crop_check_names_the_broken_rule(tmp_path):
    svc = make_service(tmp_path)
    with pytest.raises(InvalidWindow, match="section boundary"):
        svc.crop_check(MID, 5.0, 133.0)
    window = svc.crop_timeline(MID)["lengths"]["60"]["suggestions"][0]
    svc.crop_check(MID, window["start_beat"], window["end_beat"])


def test_a_missing_song_file_fails_the_crop_without_a_folder(tmp_path, cuts):
    svc = make_service(tmp_path)
    window = svc.crop_timeline(MID)["lengths"]["60"]["suggestions"][0]
    (svc.levels / NAME / "song.ogg").unlink()
    with pytest.raises(CropError, match="song file"):
        svc.crop_map(MID, window["start_beat"], window["end_beat"])
    assert sorted(p.name for p in svc.levels.iterdir()) == [NAME]


def test_map_without_standard_notes_is_refused(tmp_path):
    svc = make_service(tmp_path)
    make_360(svc.levels / NAME)
    with pytest.raises(NoNotes, match="no Standard difficulty has notes"):
        svc.crop_timeline(MID)
