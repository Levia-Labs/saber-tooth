"""BeatMods client: parsing untrusted JSON, dependency resolution, and hardened downloads."""

import hashlib
import json

import httpx
import pytest
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.mods.beatmods import BASE, BeatMods, BeatModsError, ModBuild, parse_builds, resolve

H = "a" * 32


def entry(mod_id, name, ver_id, deps=(), files=None, zip_hash=H, version="1.0.0"):
    return {
        "mod": {"id": mod_id, "name": name, "gitUrl": f"https://github.com/x/{name}"},
        "latest": {
            "id": ver_id,
            "modVersion": version,
            "zipHash": zip_hash,
            "fileSize": 10,
            "dependencies": list(deps),
            "contentHashes": [
                {"path": p, "hash": h} for p, h in (files or {f"Plugins/{name}.dll": H}).items()
            ],
        },
    }


def test_parse_reads_the_beatmods_shape():
    (b,) = parse_builds({"mods": [entry(170, "PlaylistManager", 2819, deps=[1859, 1119])]})
    assert b == ModBuild(
        170, 2819, "PlaylistManager", "1.0.0", H, "https://github.com/x/PlaylistManager",
        {"Plugins/PlaylistManager.dll": H}, (1859, 1119), 10,
    )  # fmt: skip


@pytest.mark.parametrize(
    "bad",
    [None, [], {"mods": "x"}, {"mods": [1, None, {"mod": {}}, {"mod": {"id": 1}, "latest": 5}]}],
)
def test_parse_skips_malformed_entries(bad):
    assert parse_builds(bad) == []


def test_parse_drops_a_build_with_a_bad_hash():
    assert parse_builds({"mods": [entry(1, "A", 1, zip_hash="../../etc")]}) == []


json_leaf = st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=10))
json_tree = st.recursive(
    json_leaf,
    lambda c: st.one_of(st.lists(c, max_size=4), st.dictionaries(st.text(max_size=8), c)),
    max_leaves=25,
)


@given(json_tree)
def test_parse_never_raises_on_arbitrary_json(payload):
    assert isinstance(parse_builds(payload), list)


def catalogue():
    everything = parse_builds(
        {
            "mods": [
                entry(1, "BSIPA", 1119),
                entry(58, "SongCore", 1859, deps=[1119]),
                entry(170, "PlaylistManager", 2819, deps=[1859, 1119, 2852]),
                entry(176, "BeatSaberPlaylistsLib", 2852, deps=[1859]),
            ]
        }
    )
    # for the game version: SongCore and BSIPA have other build ids than their global latest
    for_game = parse_builds(
        {
            "mods": [
                entry(1, "BSIPA", 1158, version="4.3.6"),
                entry(58, "SongCore", 1860, deps=[1158], version="3.15.3"),
                entry(170, "PlaylistManager", 2819, deps=[1860, 1158, 2852]),
                entry(176, "BeatSaberPlaylistsLib", 2852, deps=[1860]),
            ]
        }
    )
    return everything, for_game


def test_resolve_orders_dependencies_before_the_target_and_uses_game_versions():
    everything, for_game = catalogue()
    names = [(b.name, b.version) for b in resolve("PlaylistManager", everything, for_game)]
    assert names[-1][0] == "PlaylistManager"
    assert {n for n, _ in names} == {
        "BSIPA",
        "SongCore",
        "BeatSaberPlaylistsLib",
        "PlaylistManager",
    }
    assert ("SongCore", "3.15.3") in names
    assert names.index(("SongCore", "3.15.3")) < names.index(("PlaylistManager", "1.0.0"))
    assert names.index(("BSIPA", "4.3.6")) < names.index(("SongCore", "3.15.3"))


def test_resolve_reports_a_target_with_no_build_for_the_game_version():
    everything, _ = catalogue()
    with pytest.raises(BeatModsError, match="no build of PlaylistManager"):
        resolve("PlaylistManager", everything, [])


def test_resolve_reports_a_dependency_with_no_build_for_the_game_version():
    everything, for_game = catalogue()
    only = [b for b in for_game if b.name != "BeatSaberPlaylistsLib"]
    with pytest.raises(BeatModsError, match="BeatSaberPlaylistsLib"):
        resolve("PlaylistManager", everything, only)


def test_resolve_survives_dependency_cycles_and_unknown_ids():
    a = entry(1, "A", 10, deps=[11, 999])
    b = entry(2, "B", 11, deps=[10])
    everything = parse_builds({"mods": [a, b]})
    got = resolve("A", everything, everything)
    assert [x.name for x in got] == ["B", "A"]


def client(handler):
    return BeatMods(httpx.Client(transport=httpx.MockTransport(handler), base_url=BASE))


def test_mods_requests_the_verified_universal_pc_list_for_the_game_version():
    seen = []

    def handler(request):
        seen.append(request.url)
        return httpx.Response(200, json={"mods": [entry(1, "A", 1)]})

    got = client(handler).mods("1.40.8")
    assert [b.name for b in got] == ["A"]
    assert seen[0].path == "/api/mods" and seen[0].host == "beatmods.com"
    assert dict(seen[0].params) == {
        "gameName": "BeatSaber",
        "gameVersion": "1.40.8",
        "status": "verified",
        "platform": "universalpc",
    }


def test_a_game_version_that_is_not_plain_digits_is_never_sent():
    with pytest.raises(BeatModsError):
        client(lambda r: httpx.Response(200, json={})).mods("1.40.8&x=../")


def test_http_errors_and_bad_json_become_beatmods_errors():
    with pytest.raises(BeatModsError, match="503"):
        client(lambda r: httpx.Response(503)).mods()
    with pytest.raises(BeatModsError, match="not JSON"):
        client(lambda r: httpx.Response(200, content=b"<html>")).mods()

    def down(request):
        raise httpx.ConnectError("no route")

    with pytest.raises(BeatModsError, match="could not reach"):
        client(down).mods()


def build(data: bytes) -> ModBuild:
    digest = hashlib.md5(data).hexdigest()  # noqa: S324 - the published hash is MD5
    return ModBuild(1, 1, "A", "1", digest, None, {}, (), len(data))


def test_download_returns_bytes_whose_md5_matches_the_published_hash():
    data = b"zipbytes"
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, content=data)

    assert client(handler).download(build(data)) == data
    assert seen == [f"/cdn/mod/{build(data).zip_hash}.zip"]


def test_download_refuses_a_hash_mismatch():
    b = build(b"expected")
    with pytest.raises(BeatModsError, match="hash"):
        client(lambda r: httpx.Response(200, content=b"tampered")).download(b)


def test_download_refuses_an_oversized_body():
    b = build(b"x")
    with pytest.raises(BeatModsError, match="larger"):
        client(lambda r: httpx.Response(200, content=b"x" * 200)).download(b, max_bytes=100)


def test_download_does_not_follow_redirects():
    b = build(b"x")

    def handler(request):
        return httpx.Response(302, headers={"location": "https://evil.example/x.zip"})

    with pytest.raises(BeatModsError, match="302"):
        client(handler).download(b)


def test_the_catalogue_shape_survives_a_json_round_trip():
    assert len(parse_builds(json.loads(json.dumps({"mods": [entry(1, "A", 1)]})))) == 1
