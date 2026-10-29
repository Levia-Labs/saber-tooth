import hashlib
import json

from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.playlists.songcore import HashCache, songcore_hash

INFO_V2 = (
    b'{"_difficultyBeatmapSets":[{"_difficultyBeatmaps":'
    b'[{"_beatmapFilename":"a.dat"},{"_beatmapFilename":"b.dat"}]}]}'
)
HAND = "8604B1FA14305C90B9477F6599BE14068BA32A09"  # sha1(info + b"AAA" + b"BB"), uppercase


def _sha(data: bytes) -> str:
    # nosemgrep: insecure-hash-algorithm-sha1 - SongCore level id is SHA1; interop, not security
    return hashlib.sha1(data, usedforsecurity=False).hexdigest().upper()  # nosec B324


def test_v4_audio_lightshow_and_duplicates(tmp_path):
    info = (
        '﻿{"audio":{"audioDataFilename":"BPMInfo.dat"},"difficultyBeatmaps":['
        '{"beatmapDataFilename":"a.dat","lightshowDataFilename":"l.dat"},'
        '{"beatmapDataFilename":"b.dat","lightshowDataFilename":"l.dat"},'
        '{"beatmapDataFilename":"a.dat","lightshowDataFilename":"gone.dat"}]}'
    )
    folder = tmp_path / "m"
    folder.mkdir()
    (folder / "Info.dat").write_bytes(info.encode("utf-8"))
    for name, body in (("bpminfo.dat", b"AU"), ("a.dat", b"A"), ("b.dat", b"B"), ("l.dat", b"L")):
        (folder / name).write_bytes(body)
    text = info.removeprefix("﻿").encode("utf-8")  # JSON text, BOM not part of it
    want = _sha(text + b"AU" + b"A" + b"L" + b"B" + b"L" + b"A")  # duplicates hashed twice
    assert songcore_hash(folder) == want


def _v2(folder, a=b"AAA", b=b"BB", info=INFO_V2):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "Info.dat").write_bytes(info)
    (folder / "a.dat").write_bytes(a)
    (folder / "b.dat").write_bytes(b)
    return folder


def test_v2_hand_computed(tmp_path):
    assert songcore_hash(_v2(tmp_path / "m")) == HAND


def test_v4_layout_and_order(tmp_path):
    info = json.dumps(
        {"difficultyBeatmaps": [{"beatmapDataFilename": "b.dat"}, {"beatmapDataFilename": "a.dat"}]}
    ).encode()
    folder = _v2(tmp_path / "m", info=info)
    assert songcore_hash(folder) == _sha(info + b"BB" + b"AAA")


def test_missing_info_or_unlisted_file(tmp_path):
    assert songcore_hash(tmp_path) is None
    folder = _v2(tmp_path / "m")
    (folder / "b.dat").unlink()
    assert songcore_hash(folder) == _sha(INFO_V2 + b"AAA")


def test_traversal_name_skipped(tmp_path):
    info = b'{"_difficultyBeatmapSets":[{"_difficultyBeatmaps":[{"_beatmapFilename":"../x"}]}]}'
    (tmp_path / "m").mkdir()
    (tmp_path / "m" / "info.dat").write_bytes(info)
    (tmp_path / "x").write_bytes(b"secret")
    assert songcore_hash(tmp_path / "m") == _sha(info)


def test_cache_follows_rewrite(tmp_path):
    folder = _v2(tmp_path / "m")
    cache = HashCache()
    assert cache.get(folder) == HAND
    (folder / "a.dat").write_bytes(b"AAAA")
    assert cache.get(folder) != HAND


@given(
    a=st.binary(min_size=1, max_size=40),
    b=st.binary(min_size=1, max_size=40),
    pos=st.integers(min_value=0, max_value=39),
    flip=st.integers(min_value=1, max_value=255),
)
def test_any_byte_changes_hash_and_order_matters(tmp_path_factory, a, b, pos, flip):
    root = tmp_path_factory.mktemp("h")
    base = songcore_hash(_v2(root / "m", a, b))
    mutated = bytearray(a)
    mutated[pos % len(a)] ^= flip
    assert songcore_hash(_v2(root / "n", bytes(mutated), b)) != base
    swapped = songcore_hash(_v2(root / "o", b, a))
    assert (swapped == base) == (a == b)
