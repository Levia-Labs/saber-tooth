import io
import json
import stat
import zipfile
from pathlib import Path

import httpx
import pytest

from saber_tooth.beatsaver.client import BeatSaverClient
from saber_tooth.beatsaver.download import UnsafeArchive, install, safe_extract
from saber_tooth.beatsaver.models import BsMap
from saber_tooth.beatsaver.naming import folder_name_for
from saber_tooth.safe_fs import LevelsWriter
from saber_tooth.store import Store

MAPS = Path(__file__).parent / "fixtures" / "maps" / "v2_basic"


def map_files(prefix: str = "") -> dict[str, bytes]:
    return {prefix + p.name: p.read_bytes() for p in MAPS.iterdir() if p.is_file()}


def make_zip(entries: dict[str, bytes], symlinks: tuple[str, ...] = ()) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
        for name in symlinks:
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "../../etc/passwd")
    return buf.getvalue()


def build_map(mid="3a1f4", song="Neon Pulse", mapper="pulse", hash_="ab" * 20) -> BsMap:
    return BsMap(
        mid, song, song, "", "Artist", mapper, 120.0, 100, 0.97, 1, 0, (), False, hash_,
        f"https://r2cdn.beatsaver.com/{mid}.zip", "", "", (), "",
    )  # fmt: skip


def client_for(body: bytes, status: int = 200) -> BeatSaverClient:
    transport = httpx.MockTransport(lambda r: httpx.Response(status, content=body))
    return BeatSaverClient(transport, sleep=lambda s: None)


@pytest.fixture
def env(tmp_path):
    levels = tmp_path / "levels"
    levels.mkdir()
    (levels / "Original").mkdir()
    (levels / "Original" / "info.dat").write_text("{}", encoding="utf-8")
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    return levels, tmp, Store(tmp_path / "s.db")


def run(env, entries, bs=None, symlinks=()):
    levels, tmp, store = env
    client = client_for(make_zip(entries, symlinks))
    return install(client, LevelsWriter(levels), store, bs or build_map(), tmp)


@pytest.mark.parametrize(
    "bad", ["../x", "a/../../x", "/x", "C:/x", "c:\\x", "a\\..\\..\\x", "..\\x"]
)
def test_unsafe_paths_refused(tmp_path, bad):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip({**map_files(), bad: b"x"}))
    with pytest.raises(UnsafeArchive):
        safe_extract(z, tmp_path / "out", 10**7, 100)
    assert not (tmp_path / "x").exists()


def test_symlink_entry_refused(tmp_path):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip(map_files(), symlinks=("link",)))
    with pytest.raises(UnsafeArchive, match="symlink"):
        safe_extract(z, tmp_path / "out", 10**7, 100)


def test_too_many_entries_and_too_large(tmp_path):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip({f"f{i}": b"x" for i in range(20)} | map_files()))
    with pytest.raises(UnsafeArchive, match="too many"):
        safe_extract(z, tmp_path / "o1", 10**7, 10)
    with pytest.raises(UnsafeArchive, match="size"):
        safe_extract(z, tmp_path / "o2", 100, 100)


def test_lying_size_header_is_caught_while_streaming(tmp_path, monkeypatch):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip({"info.dat": b"x" * 5000}))
    real = zipfile.ZipFile.infolist

    def fake(self):
        infos = real(self)
        for i in infos:
            i.file_size = 1
        return infos

    monkeypatch.setattr(zipfile.ZipFile, "infolist", fake)
    with pytest.raises(UnsafeArchive, match=r"size|corrupt"):
        safe_extract(z, tmp_path / "out", 100, 100)


def test_corrupt_zip(tmp_path):
    z = tmp_path / "a.zip"
    z.write_bytes(b"not a zip at all")
    with pytest.raises(UnsafeArchive):
        safe_extract(z, tmp_path / "out", 10**7, 100)


def test_two_info_dat_refused_and_none_refused(tmp_path):
    z = tmp_path / "a.zip"
    z.write_bytes(make_zip({**map_files("A/"), **map_files("B/")}))
    with pytest.raises(UnsafeArchive, match="more than one"):
        safe_extract(z, tmp_path / "o1", 10**7, 100)
    z.write_bytes(make_zip({"readme.txt": b"hi"}))
    with pytest.raises(UnsafeArchive, match=r"no Info.dat"):
        safe_extract(z, tmp_path / "o2", 10**7, 100)
    z.write_bytes(make_zip(map_files("a/b/")))
    with pytest.raises(UnsafeArchive, match="deeply"):
        safe_extract(z, tmp_path / "o3", 10**7, 100)


def test_nested_single_root_installs(env):
    out = run(env, map_files("Song/"))
    assert out.status == "installed", out.reason
    levels = env[0]
    assert (levels / out.folder / "info.dat").is_file()
    assert not (levels / out.folder / "Song").exists()


def test_success_writes_folder_and_records_bs(env):
    levels, _, store = env
    out = run(env, map_files())
    assert out.folder == "3a1f4 (Neon Pulse - pulse)" and out.reason is None
    assert (levels / out.folder / "song.ogg").is_file()
    rows = {r["folder"]: r for r in store.bs_rows()}
    assert rows[out.folder]["bs_id"] == "3a1f4" and rows[out.folder]["bs_hash"] == "ab" * 20
    assert (levels / "Original" / "info.dat").read_text(encoding="utf-8") == "{}"
    assert sorted(p.name for p in levels.iterdir()) == ["3a1f4 (Neon Pulse - pulse)", "Original"]
    assert not list(env[1].iterdir())  # temp area cleaned


def test_installed_map_is_skipped(env):
    first = run(env, map_files())
    assert first.status == "installed"
    same_key = run(env, map_files(), bs=build_map(hash_="cd" * 20))
    assert same_key.status == "skipped"
    same_hash = run(env, map_files(), bs=build_map(mid="999", song="Other"))
    assert same_hash.status == "skipped"
    assert len(list(env[0].iterdir())) == 2


def test_manually_installed_folder_with_key_prefix_is_skipped(env):
    levels, _, store = env
    (levels / "3a1f4 (Old - Name)").mkdir()
    store.upsert_map("m" * 12, "3a1f4 (Old - Name)", "Old", "Name", "", None)
    assert run(env, map_files()).status == "skipped"


def test_noodle_map_refused_with_reason(env):
    levels = env[0]
    info = json.loads((MAPS / "info.dat").read_text(encoding="utf-8"))
    info["_customData"] = {"_requirements": ["Noodle Extensions"]}
    out = run(env, {**map_files(), "info.dat": json.dumps(info).encode("utf-8")})
    assert out.status == "failed" and "Noodle Extensions" in out.reason
    assert [p.name for p in levels.iterdir()] == ["Original"]


def test_unreadable_map_fails_without_leaving_files(env):
    out = run(env, {"info.dat": b"not json"})
    assert out.status == "failed"
    assert [p.name for p in env[0].iterdir()] == ["Original"]


def test_unsafe_archive_fails_cleanly(env):
    out = run(env, {**map_files(), "../evil": b"x"})
    assert out.status == "failed" and "unsafe" in out.reason
    assert [p.name for p in env[0].iterdir()] == ["Original"]


def test_download_error_and_bad_host_fail(env):
    levels, tmp, store = env
    out = install(client_for(b"", 404), LevelsWriter(levels), store, build_map(), tmp)
    assert out.status == "failed"
    bad = BsMap.from_dict({**build_map().to_dict(), "download_url": "http://evil.example/a.zip"})
    out = install(client_for(b""), LevelsWriter(levels), store, bad, tmp)
    assert out.status == "failed" and "non-BeatSaver" in out.reason


def test_name_collision_never_overwrites(env):
    levels, tmp, store = env
    (levels / "3a1f4 (Neon Pulse - pulse)").mkdir()
    (levels / "3a1f4 (Neon Pulse - pulse)" / "keep.txt").write_text("k", encoding="utf-8")
    out = install(client_for(make_zip(map_files())), LevelsWriter(levels), store, build_map(), tmp)
    assert out.folder == "3a1f4 (Neon Pulse - pulse) 2"
    assert (levels / "3a1f4 (Neon Pulse - pulse)" / "keep.txt").is_file()


def test_folder_name_sanitised():
    bs = build_map(song='A<b>:"c"/d\\e|f?g*\x01h', mapper="  ..Dots.. ")
    assert folder_name_for(bs) == "3a1f4 (Abcdefgh - Dots)"
    assert folder_name_for(build_map(song="", mapper="")) == "3a1f4 (Unknown - Unknown)"
    with pytest.raises(ValueError):
        folder_name_for(build_map(mid="../x"))
