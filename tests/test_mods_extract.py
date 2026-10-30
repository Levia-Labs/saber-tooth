"""Safe extraction of mod zips into Plugins, Libs and IPA of a game folder."""

import hashlib
import io
import os
import zipfile

import pytest
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.mods.beatmods import ModBuild
from saber_tooth.mods.extract import (
    InstallError,
    mod_state,
    read_zip,
    safe_entry,
    write_new,
)


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()  # noqa: S324 - BeatMods publishes MD5


def make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


def build(files: dict[str, bytes], name="PlaylistManager") -> ModBuild:
    return ModBuild(
        1, 1, name, "1.7.3", "a" * 32, None, {p: md5(d) for p, d in files.items()}, (), 1
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Plugins/A.dll", "Plugins/A.dll"),
        ("Libs/sub/B.dll", "Libs/sub/B.dll"),
        ("IPA/Data/x.dll", "IPA/Data/x.dll"),
        ("../A.dll", None),
        ("Plugins/../../A.dll", None),
        ("Plugins/../Libs/A.dll", None),
        ("/Plugins/A.dll", None),
        ("C:/Plugins/A.dll", None),
        ("Plugins\\..\\A.dll", None),
        ("Plugins\\A.dll", None),
        ("Beat Saber_Data/Managed/A.dll", None),
        ("UserData/x.json", None),
        ("Plugins", None),
        ("Plugins/", None),
        ("Plugins/\x00.dll", None),
        ("plugins/A.dll", None),
        ("Plugins//A.dll", None),
        ("Plugins/./A.dll", None),
        ("", None),
    ],
)
def test_safe_entry_accepts_only_clean_paths_in_the_allowed_folders(raw, expected):
    assert safe_entry(raw) == expected


@given(st.text(max_size=60))
def test_safe_entry_never_yields_an_escaping_path(raw):
    got = safe_entry(raw)
    if got is not None:
        parts = got.split("/")
        assert parts[0] in ("Plugins", "Libs", "IPA") and len(parts) >= 2
        assert all(p not in ("", ".", "..") for p in parts)
        assert "\\" not in got and ":" not in got and "\x00" not in got


def test_read_zip_returns_files_checked_against_the_published_hashes():
    files = {"Plugins/PlaylistManager.dll": b"dll", "Plugins/PlaylistManager.pdb": b"pdb"}
    got = read_zip(build(files), make_zip(files))
    assert dict(got) == files


def test_read_zip_refuses_a_file_that_differs_from_its_published_hash():
    b = build({"Plugins/A.dll": b"good"})
    with pytest.raises(InstallError, match="hash"):
        read_zip(b, make_zip({"Plugins/A.dll": b"evil"}))


def test_read_zip_refuses_an_entry_outside_the_allowed_folders():
    files = {"Plugins/A.dll": b"x", "Beat Saber_Data/Managed/Assembly.dll": b"y"}
    with pytest.raises(InstallError, match="outside"):
        read_zip(build({"Plugins/A.dll": b"x"}), make_zip(files))


def test_read_zip_refuses_traversal_entries():
    with pytest.raises(InstallError, match="outside"):
        read_zip(build({}), make_zip({"Plugins/../../evil.dll": b"x"}))


def test_read_zip_refuses_a_non_zip_and_a_bomb():
    with pytest.raises(InstallError, match="not a zip"):
        read_zip(build({}), b"not a zip")
    big = make_zip({"Plugins/big.bin": b"0" * 5000})
    with pytest.raises(InstallError, match="too large"):
        read_zip(build({}), big, max_total=1000)


def test_read_zip_ignores_directory_entries():
    got = read_zip(build({}), make_zip({"Plugins/": b""}))
    assert got == []


def test_write_new_creates_files_and_parents(tmp_path):
    made = write_new(tmp_path, [("Plugins/A.dll", b"a"), ("Libs/deep/B.dll", b"b")])
    assert (tmp_path / "Plugins" / "A.dll").read_bytes() == b"a"
    assert (tmp_path / "Libs" / "deep" / "B.dll").read_bytes() == b"b"
    assert len(made) == 2


def test_write_new_never_overwrites_an_existing_file(tmp_path):
    (tmp_path / "Plugins").mkdir()
    (tmp_path / "Plugins" / "A.dll").write_bytes(b"newer")
    made = write_new(tmp_path, [("Plugins/A.dll", b"older"), ("Plugins/B.dll", b"b")])
    assert (tmp_path / "Plugins" / "A.dll").read_bytes() == b"newer"
    assert made == [tmp_path / "Plugins" / "B.dll"]


def test_write_new_rolls_back_when_a_write_fails(tmp_path):
    (tmp_path / "Plugins").mkdir()
    (tmp_path / "Libs").write_bytes(b"a file where a folder must go")
    with pytest.raises(InstallError):
        write_new(tmp_path, [("Plugins/A.dll", b"a"), ("Libs/B.dll", b"b")])
    assert not (tmp_path / "Plugins" / "A.dll").exists()


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_write_new_refuses_a_symlinked_target_folder(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "game"
    root.mkdir()
    (root / "Plugins").symlink_to(outside, target_is_directory=True)
    with pytest.raises(InstallError, match="link"):
        write_new(root, [("Plugins/A.dll", b"a")])
    assert list(outside.iterdir()) == []


def test_write_new_refuses_paths_that_are_not_safe_entries(tmp_path):
    with pytest.raises(InstallError):
        write_new(tmp_path, [("../escape.dll", b"x")])
    assert not (tmp_path.parent / "escape.dll").exists()


def test_mod_state_missing_current_and_other(tmp_path):
    files = {"Plugins/A.dll": b"v1", "Plugins/A.pdb": b"sym"}
    b = build(files)
    assert mod_state(tmp_path, b) == "missing"
    write_new(tmp_path, list(files.items()))
    assert mod_state(tmp_path, b) == "current"
    (tmp_path / "Plugins" / "A.dll").write_bytes(b"v2 from someone else")
    assert mod_state(tmp_path, b) == "other"


def test_a_missing_pdb_does_not_make_a_current_mod_missing(tmp_path):
    files = {"Plugins/A.dll": b"v1", "Plugins/A.pdb": b"sym"}
    write_new(tmp_path, [("Plugins/A.dll", b"v1")])
    assert mod_state(tmp_path, build(files)) == "current"
