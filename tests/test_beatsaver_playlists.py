import base64
import json

import pytest

from saber_tooth.beatsaver.playlists import PlaylistsDisabled, export_bplist
from tests.test_beatsaver_search import build_map


def maps():
    return [build_map("3a1f4"), build_map("3a1f5")]


def test_json_shape(tmp_path):
    path = export_bplist("Chill", maps(), tmp_path, cover=b"\x89PNG")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "Chill.bplist"
    assert doc["playlistTitle"] == "Chill" and doc["playlistAuthor"] == "saber-tooth"
    assert doc["songs"][0] == {
        "key": "3a1f4", "hash": "3a1f4" * 4,
        "songName": "Song", "levelAuthorName": "Mapper",
    }  # fmt: skip
    assert base64.b64decode(doc["image"].removeprefix("base64,")) == b"\x89PNG"


def test_no_cover_means_no_image(tmp_path):
    doc = json.loads(export_bplist("x", maps(), tmp_path).read_text(encoding="utf-8"))
    assert "image" not in doc


def test_name_is_sanitised_and_stays_inside(tmp_path):
    path = export_bplist('..\\evil/<n>:"a"|?*', maps(), tmp_path)
    assert path.parent == tmp_path and path.suffix == ".bplist"
    assert not set('<>:"/\\|?*') & set(path.name)


def test_never_overwrites(tmp_path):
    first = export_bplist("Mix", maps(), tmp_path)
    first.write_text("keep", encoding="utf-8")
    second = export_bplist("Mix", maps(), tmp_path)
    third = export_bplist("Mix", maps(), tmp_path)
    assert [p.name for p in (second, third)] == ["Mix (2).bplist", "Mix (3).bplist"]
    assert first.read_text(encoding="utf-8") == "keep"


def test_empty_title_gets_default(tmp_path):
    assert export_bplist("   ", maps(), tmp_path).name == "Playlist.bplist"


def test_refuses_when_dir_unset_or_missing(tmp_path):
    with pytest.raises(PlaylistsDisabled):
        export_bplist("x", maps(), None)
    with pytest.raises(PlaylistsDisabled):
        export_bplist("x", maps(), tmp_path / "missing")
