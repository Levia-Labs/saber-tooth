"""Finding the Beat Saber folder: setting, env, derived from the levels folder; its version."""

import pytest

from saber_tooth.mods import game
from saber_tooth.mods.game import find_game, game_running, game_version


def make_game(tmp_path, version="1.40.8", name="Beat Saber"):
    root = tmp_path / name
    (root / "Beat Saber_Data" / "CustomLevels").mkdir(parents=True)
    if version is not None:
        (root / "BeatSaberVersion.txt").write_text(version + "\n", encoding="utf-8")
    return root


def test_the_saved_setting_wins_over_env_and_levels(tmp_path):
    a, b = make_game(tmp_path, name="a"), make_game(tmp_path, name="b")
    found = find_game(a, str(b), b / "Beat Saber_Data" / "CustomLevels")
    assert (found.root, found.source) == (a, "setting")


def test_env_is_used_when_no_setting(tmp_path):
    root = make_game(tmp_path)
    found = find_game(None, str(root), tmp_path / "elsewhere")
    assert (found.root, found.source) == (root, "env")


def test_the_game_root_is_derived_from_a_customlevels_mount(tmp_path):
    root = make_game(tmp_path)
    found = find_game(None, None, root / "Beat Saber_Data" / "CustomLevels")
    assert (found.root, found.source) == (root, "levels")


def test_a_levels_folder_elsewhere_gives_no_game(tmp_path):
    (tmp_path / "levels").mkdir()
    found = find_game(None, None, tmp_path / "levels")
    assert found.root is None and found.source is None


def test_a_set_path_that_is_not_a_game_is_skipped(tmp_path):
    (tmp_path / "empty").mkdir()
    root = make_game(tmp_path)
    found = find_game(tmp_path / "empty", str(root), tmp_path / "x")
    assert found.root == root


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.40.8\n", "1.40.8"),
        ("  1.39.1 ", "1.39.1"),
        ("1.40.8_4561", None),
        ("", None),
        ("x", None),
    ],
)
def test_the_version_file_is_parsed_strictly(tmp_path, text, expected):
    root = make_game(tmp_path, version=None)
    (root / "BeatSaberVersion.txt").write_text(text, encoding="utf-8")
    assert game_version(root) == expected


def test_a_missing_version_file_gives_none(tmp_path):
    assert game_version(make_game(tmp_path, version=None)) is None


def test_running_is_none_where_it_cannot_be_detected(monkeypatch):
    monkeypatch.setattr(game, "_process_names", lambda: None)
    assert game_running() is None


def test_running_matches_the_game_executable(monkeypatch):
    monkeypatch.setattr(game, "_process_names", lambda: ["python.exe", "Beat Saber.exe"])
    assert game_running() is True
    monkeypatch.setattr(game, "_process_names", lambda: ["python.exe"])
    assert game_running() is False
