"""Tests for the strict map-folder deletion guard; every tree lives under tmp_path."""

import json
import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from saber_tooth.api import create_app
from saber_tooth.map_folder_guard import MAX_FILES, check_map_folder
from saber_tooth.service import map_id_for
from tests.test_service import NAME, _make

V2 = {
    "_version": "2.0.0",
    "_songName": "S",
    "_songFilename": "song.ogg",
    "_coverImageFilename": "cover.jpg",
    "_difficultyBeatmapSets": [
        {"_difficultyBeatmaps": [{"_difficulty": "Easy", "_beatmapFilename": "easy.dat"}]}
    ],
}
V4 = {
    "version": "4.0.0",
    "song": {"title": "S"},
    "audio": {"songFilename": "song.ogg", "audioDataFilename": "Audio.dat"},
    "coverImageFilename": "cover.png",
    "difficultyBeatmaps": [{"beatmapDataFilename": "E.dat", "lightshowDataFilename": "L.dat"}],
}
FILES_V2 = ("Info.dat", "Easy.dat", "song.ogg", "cover.jpg")
FILES_V4 = ("Info.dat", "E.dat", "L.dat", "Audio.dat", "song.ogg", "cover.png")
fresh = settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=40)


def build(tmp_path: Path, info: dict, files: tuple[str, ...], name: str | None = None) -> Path:
    root = tmp_path / "levels"
    root.mkdir(exist_ok=True)
    folder = root / (name or uuid.uuid4().hex)
    folder.mkdir()
    for f in files:
        data = json.dumps(info) if f.lower() == "info.dat" else "{}"
        (folder / f).write_text(data, encoding="utf-8")
    return folder


@pytest.mark.parametrize(("info", "files"), [(V2, FILES_V2), (V4, FILES_V4)])
def test_minimal_maps_pass(tmp_path, info, files):
    folder = build(tmp_path, info, files)
    assert check_map_folder(folder, folder.parent) == []
    assert check_map_folder(folder, folder.parent, map_id_for(folder.name)) == []
    assert check_map_folder(folder, folder.parent, "0" * 12) != []


def test_lowercase_info_bpminfo_and_case_insensitive_refs(tmp_path):
    folder = build(tmp_path, V2, ("info.dat", "EASY.DAT", "SONG.OGG", "Cover.JPG", "BPMInfo.dat"))
    assert check_map_folder(folder, folder.parent) == []


@given(sub=st.text("abcdef", min_size=1, max_size=6), v4=st.booleans())
@fresh
def test_subdirectory_refused(tmp_path, sub, v4):
    folder = build(tmp_path, V4 if v4 else V2, FILES_V4 if v4 else FILES_V2)
    (folder / sub).mkdir(exist_ok=True)
    assert check_map_folder(folder, folder.parent)


@given(ext=st.sampled_from([".txt", ".exe", ".json", ".zip", ".bak", "", ".dat.txt"]))
@fresh
def test_foreign_extension_refused(tmp_path, ext):
    folder = build(tmp_path, V2, FILES_V2)
    (folder / f"extra{ext}").write_text("x", encoding="utf-8")
    assert check_map_folder(folder, folder.parent)


@given(name=st.text("abcxyz", min_size=1, max_size=6))
@fresh
def test_unreferenced_allowed_extension_refused(tmp_path, name):
    folder = build(tmp_path, V2, FILES_V2)
    (folder / f"zz{name}.wav").write_text("x", encoding="utf-8")
    reasons = check_map_folder(folder, folder.parent)
    assert any("unreferenced" in r for r in reasons)


@given(depth=st.integers(1, 3))
@fresh
def test_outside_root_or_nested_refused(tmp_path, depth):
    folder = build(tmp_path, V2, FILES_V2)
    other = tmp_path / "other"
    other.mkdir(exist_ok=True)
    assert check_map_folder(folder, other)
    nested = folder
    for i in range(depth):
        nested = nested / f"n{i}"
        nested.mkdir(exist_ok=True)
        ignore = shutil.ignore_patterns("n*")
        shutil.copytree(folder, nested / "m", dirs_exist_ok=True, ignore=ignore)
        assert check_map_folder(nested / "m", folder.parent)
        nested = nested / "m"


def test_root_and_bad_names_refused(tmp_path):
    folder = build(tmp_path, V2, FILES_V2)
    root = folder.parent
    assert check_map_folder(root, root)
    assert check_map_folder(root / "..", root)
    hidden = build(tmp_path, V2, FILES_V2, name=".hidden")
    assert check_map_folder(hidden, root)


def test_symlink_refused(tmp_path):
    folder = build(tmp_path, V2, FILES_V2)
    link = folder.parent / "link"
    try:
        link.symlink_to(folder, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert check_map_folder(link, folder.parent)
    inner = folder / "song2.ogg"
    try:
        inner.symlink_to(folder / "song.ogg")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert check_map_folder(folder, folder.parent)


def test_hardlink_refused(tmp_path):
    folder = build(tmp_path, V2, FILES_V2)
    try:
        (tmp_path / "linked.ogg").hardlink_to(folder / "song.ogg")
    except (OSError, NotImplementedError):
        pytest.skip("hardlinks unavailable")
    assert check_map_folder(folder, folder.parent)


def test_too_many_files_refused(tmp_path):
    folder = build(tmp_path, V2, FILES_V2)
    for i in range(MAX_FILES):
        (folder / f"x{i}.dat").write_text("{}", encoding="utf-8")
    assert any("more than" in r for r in check_map_folder(folder, folder.parent))


def test_too_large_refused(tmp_path, monkeypatch):
    folder = build(tmp_path, V2, FILES_V2)
    monkeypatch.setattr("saber_tooth.map_folder_guard.MAX_BYTES", 1)
    (folder / "song.ogg").write_bytes(b"xx")
    assert any("larger" in r for r in check_map_folder(folder, folder.parent))


@pytest.mark.parametrize(
    "drop", ["Info.dat", "Easy.dat", "song.ogg", "cover.jpg"], ids=lambda d: f"missing-{d}"
)
def test_missing_referenced_file_refused(tmp_path, drop):
    folder = build(tmp_path, V2, tuple(f for f in FILES_V2 if f != drop))
    assert check_map_folder(folder, folder.parent)


def test_bad_info_refused(tmp_path):
    for body in ("not json", "[]", json.dumps({"_version": "2.0.0"}), json.dumps({"version": "4"})):
        folder = build(tmp_path, V2, FILES_V2)
        (folder / "Info.dat").write_text(body, encoding="utf-8")
        assert check_map_folder(folder, folder.parent)
    folder = build(tmp_path, V2, FILES_V2)
    (folder / "Info.dat").write_bytes(b"\xff\xfe")
    assert check_map_folder(folder, folder.parent)


def test_no_difficulty_refused(tmp_path):
    info = {**V2, "_difficultyBeatmapSets": []}
    folder = build(tmp_path, info, ("Info.dat", "song.ogg", "cover.jpg"))
    assert any("no difficulty" in r for r in check_map_folder(folder, folder.parent))


def test_service_delete_409_with_reasons(tmp_path):
    svc = _make(tmp_path)
    mid = map_id_for(NAME)
    (svc.levels / NAME / "notes.txt").write_text("keep", encoding="utf-8")
    client = TestClient(create_app(svc), base_url="http://localhost")
    resp = client.delete(f"/api/maps/{mid}")
    assert resp.status_code == 409
    assert "notes.txt" in resp.text
    assert (svc.levels / NAME / "notes.txt").exists()
    assert svc.store.get_map(mid) is not None


def _with_custom(custom: dict) -> dict:
    return {**V2, "_customData": custom}


def test_icon_named_in_custom_data_counts_as_referenced(tmp_path):
    info = _with_custom({"_contributors": [{"_iconPath": "OC_Beat_Saber 1mb.PNG"}]})
    folder = build(tmp_path, info, (*FILES_V2, "oc_beat_saber 1MB.png"))
    assert check_map_folder(folder, folder.parent) == []


@given(bad=st.sampled_from(["../a.png", "sub/a.png", "sub\a.png", "..", "x..y/a.png"]))
@fresh
def test_path_like_values_never_reference(tmp_path, bad):
    folder = build(tmp_path, _with_custom({"_iconPath": bad}), (*FILES_V2, "a.png"))
    assert any("unreferenced" in r for r in check_map_folder(folder, folder.parent))


def test_cinema_video_json_allowed_when_small_object(tmp_path):
    folder = build(tmp_path, V2, FILES_V2)
    (folder / "cinema-video.json").write_text('{"videoFile": "v.mp4"}', encoding="utf-8")
    assert check_map_folder(folder, folder.parent) == []


@pytest.mark.parametrize("kind", ["array", "garbage", "big"])
def test_cinema_video_json_refused_when_invalid_or_big(tmp_path, kind):
    body = {"array": "[1]", "garbage": "not json", "big": json.dumps({"a": "x" * 70000})}[kind]
    folder = build(tmp_path, V2, FILES_V2)
    (folder / "cinema-video.json").write_text(body, encoding="utf-8")
    assert check_map_folder(folder, folder.parent)


def test_other_json_names_still_refused(tmp_path):
    folder = build(tmp_path, V2, FILES_V2)
    (folder / "Cinema-Video.json").write_text("{}", encoding="utf-8")
    assert check_map_folder(folder, folder.parent)


def test_vivify_only_when_referenced(tmp_path):
    folder = build(tmp_path, V2, (*FILES_V2, "b.vivify"))
    assert check_map_folder(folder, folder.parent)
    folder = build(tmp_path, _with_custom({"bundle": "B.vivify"}), (*FILES_V2, "b.vivify"))
    assert check_map_folder(folder, folder.parent) == []
