import io
import zipfile

import httpx
import pytest

from saber_tooth.beatsaver.client import BeatSaverClient
from saber_tooth.beatsaver.download import UnsafeArchive, install, safe_extract
from saber_tooth.safe_fs import LevelsWriter
from saber_tooth.store import Store
from tests.test_beatsaver_download import build_map, client_for, make_zip, map_files


@pytest.fixture
def env(tmp_path):
    levels = tmp_path / "levels"
    levels.mkdir()
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    return levels, tmp, Store(tmp_path / "s.db")


def run(env, entries):
    levels, tmp, store = env
    return install(client_for(make_zip(entries)), LevelsWriter(levels), store, build_map(), tmp)


@pytest.mark.parametrize(
    "bad", ["a:b", "data.dat:stream", "x\x01y", "a<b", "a|b", "a?b", "a*b", "a.", "a ",
            "CON", "nul.txt", "Com1", "d/LPT9.dat", "d/a:b"],
)  # fmt: skip
def test_windows_unsafe_entries_refused(tmp_path, bad):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip({**map_files(), bad: b"x"}))
    with pytest.raises(UnsafeArchive):
        safe_extract(z, tmp_path / "out", 10**7, 100)


def test_case_variant_duplicates_refused(tmp_path):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip({**map_files(), "Song.OGG": b"a", "song.ogg": b"b"}))
    with pytest.raises(UnsafeArchive, match=r"clash|duplicate"):
        safe_extract(z, tmp_path / "out", 10**7, 100)


def test_nfc_variant_duplicates_refused(tmp_path):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip({**map_files(), "café.txt": b"a", "café.txt": b"b"}))
    with pytest.raises(UnsafeArchive, match=r"clash|duplicate"):
        safe_extract(z, tmp_path / "out", 10**7, 100)


def test_file_and_directory_clash_refused(tmp_path):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip({**map_files(), "Art": b"a", "art/cover.png": b"b"}))
    with pytest.raises(UnsafeArchive, match=r"clash|duplicate"):
        safe_extract(z, tmp_path / "out", 10**7, 100)
    z.write_bytes(make_zip({**map_files(), "art/cover.png": b"b", "ART": b"a"}))
    with pytest.raises(UnsafeArchive, match=r"clash|duplicate"):
        safe_extract(z, tmp_path / "out2", 10**7, 100)


def test_compression_ratio_cap(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in map_files().items():
            zf.writestr(name, data)
        zf.writestr("bomb.bin", b"\0" * (3 * 1024 * 1024))
    z = tmp_path / "a.zip"
    z.write_bytes(buf.getvalue())
    with pytest.raises(UnsafeArchive, match="ratio"):
        safe_extract(z, tmp_path / "out", 10**9, 100)


def test_forged_size_header_and_ratio_enforced_while_streaming(tmp_path, monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in map_files().items():
            zf.writestr(name, data)
        zf.writestr("bomb.bin", b"\0" * (3 * 1024 * 1024))
    z = tmp_path / "a.zip"
    z.write_bytes(buf.getvalue())
    real = zipfile.ZipFile.infolist

    def forged(self):
        infos = real(self)
        for i in infos:
            i.file_size = 10
        return infos

    monkeypatch.setattr(zipfile.ZipFile, "infolist", forged)
    with pytest.raises(UnsafeArchive, match=r"ratio|size|corrupt"):
        safe_extract(z, tmp_path / "out", 10**9, 100)


def test_oversized_info_dat_refused(env):
    files = map_files()
    files["info.dat"] = b"{" + b" " * (5 * 1024 * 1024 + 1) + b"}"
    out = run(env, files)
    assert out.status == "failed" and "MB" in out.reason


def test_deeply_nested_info_dat_fails_cleanly(env):
    files = map_files()
    files["info.dat"] = b"[" * 100000 + b"]" * 100000
    out = run(env, files)
    assert out.status == "failed" and out.reason


def test_rate_limit_marks_outcome(env):
    levels, tmp, store = env
    transport = httpx.MockTransport(lambda r: httpx.Response(429, headers={"retry-after": "0"}))
    client = BeatSaverClient(transport, sleep=lambda s: None)
    out = install(client, LevelsWriter(levels), store, build_map(), tmp)
    assert out.status == "failed" and out.rate_limited


def test_deadline_stops_download(env):
    levels, tmp, store = env
    client = client_for(make_zip(map_files()))
    out = install(client, LevelsWriter(levels), store, build_map(), tmp, deadline=-1.0)
    assert out.status == "failed" and "timed out" in out.reason
