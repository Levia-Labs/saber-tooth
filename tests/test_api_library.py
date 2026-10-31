# ruff: noqa: F811
import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.api import create_app
from saber_tooth.api.library import MAX_COVER_BYTES, parse_query
from tests.bg_helpers import settle
from tests.test_api import MID, NAME, client, svc  # noqa: F401


@pytest.fixture
def web_client(svc, tmp_path):
    """Client over a stand-in build output, so tests do not need `task st:web:build`."""
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>saber-tooth</title>", encoding="utf-8")
    (web / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    (web / "assets" / "index-abc12345.js").write_text("export {};", encoding="utf-8")
    with TestClient(create_app(svc, web=web), base_url="http://localhost") as c:
        c.web = web  # type: ignore[attr-defined]
        yield c


def test_item_has_difficulties_status_and_cover(client):
    item = client.get(f"/api/maps/{MID}").json()
    assert {"Easy", "Hard", "ExpertPlus"} <= set(item["difficulties"])
    assert item["status"] == "unscanned" and item["scanned_at"] is None
    assert item["cover_url"] == f"/api/maps/{MID}/cover"
    assert client.get("/api/maps").json()["items"][0] == item


def test_unknown_or_malformed_map_is_404(client):
    assert client.get("/api/maps/" + "f" * 12).status_code == 404
    assert client.get("/api/maps/..%2F..%2Fetc").status_code == 404
    assert client.get("/api/maps/..%2F..%2Fetc/cover").status_code == 404


@pytest.mark.parametrize(
    "query",
    ["limit=0", "limit=101", "limit=x", "limit=-1", "offset=-1", "offset=1.5", "sort=id",
     "sort=title;drop", "order=up", "status=bad", "q=" + "a" * 201],
)  # fmt: skip
def test_bad_query_values_are_400(client, query):
    resp = client.get(f"/api/maps?{query}")
    assert resp.status_code == 400 and set(resp.json()) == {"error"}


def test_query_filters_sort_and_pages(client, svc):
    import shutil

    shutil.copytree(svc.levels / NAME, svc.levels / "Zulu")
    info = svc.levels / "Zulu" / "info.dat"
    info.write_text(info.read_text(encoding="utf-8").replace('"Basic"', '"Zulu"'), encoding="utf-8")
    client.get("/api/maps")  # starts the background re-index
    settle(svc)
    page = client.get("/api/maps?limit=1&sort=title&order=desc").json()
    assert page["total"] == 2 and page["limit"] == 1
    assert [m["folder"] for m in page["items"]] == ["Zulu"]
    nxt = client.get("/api/maps?limit=1&offset=1&order=desc").json()
    assert [m["folder"] for m in nxt["items"]] == [NAME]
    assert client.get("/api/maps?q=ZUL").json()["total"] == 1
    assert client.get("/api/maps?status=ok").json() == {
        "items": [], "total": 0, "offset": 0, "limit": 40,
    }  # fmt: skip
    assert client.get("/api/maps?status=unscanned").json()["total"] == 2


def test_parse_query_defaults():
    q = parse_query({})
    assert (q.offset, q.limit, q.sort, q.order, q.q, q.status) == (0, 40, "title", "asc", "", ())


def test_cover_serves_bytes_with_cache_headers_and_304(client, svc):
    (svc.levels / NAME / "cover.jpg").write_bytes(b"\xff\xd8jpegdata")
    resp = client.get(f"/api/maps/{MID}/cover")
    assert resp.status_code == 200 and resp.content == b"\xff\xd8jpegdata"
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.headers["cache-control"] == "private, max-age=86400"
    etag = resp.headers["etag"]
    again = client.get(f"/api/maps/{MID}/cover", headers={"if-none-match": etag})
    assert again.status_code == 304 and again.content == b"" and again.headers["etag"] == etag
    other = client.get(f"/api/maps/{MID}/cover", headers={"if-none-match": '"nope"'})
    assert other.status_code == 200


def test_cover_missing_wrong_type_or_oversize_is_404(client, svc):
    cover = svc.levels / NAME / "cover.jpg"
    cover.unlink()
    assert client.get(f"/api/maps/{MID}/cover").status_code == 404
    assert client.get(f"/api/maps/{MID}").json()["cover_url"] is None
    cover.write_bytes(b"x" * (MAX_COVER_BYTES + 1))
    assert client.get(f"/api/maps/{MID}/cover").status_code == 404
    assert client.get(f"/api/maps/{MID}").json()["cover_url"] is None


def _set_cover(svc, name: str) -> None:
    info = svc.levels / NAME / "info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace('"cover.jpg"', f'"{name}"'), encoding="utf-8"
    )


@pytest.mark.parametrize(
    "name",
    ["../secret.png", "..\\secret.png", "sub/c.png", "C:c.png", "cover.svg", "cover.dat", ".."],
)
def test_cover_name_escape_or_bad_extension_is_404(client, svc, name):
    (svc.levels.parent / "secret.png").write_bytes(b"secret")
    _set_cover(svc, name)
    assert client.get(f"/api/maps/{MID}/cover").status_code == 404
    assert client.get(f"/api/maps/{MID}").json()["cover_url"] is None


def test_cover_symlink_out_of_folder_is_404(client, svc):
    outside = svc.levels.parent / "secret.png"
    outside.write_bytes(b"secret")
    link = svc.levels / NAME / "cover.png"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    _set_cover(svc, "cover.png")
    assert client.get(f"/api/maps/{MID}/cover").status_code == 404


def test_cover_is_case_insensitive_match_inside_folder(client, svc):
    (svc.levels / NAME / "cover.jpg").rename(svc.levels / NAME / "COVER.JPG")
    assert client.get(f"/api/maps/{MID}/cover").status_code == 200


AUDIO = bytes(range(256)) * 4


def _song(svc, data: bytes = AUDIO):
    song = svc.levels / NAME / "song.ogg"
    song.write_bytes(data)
    return song


def test_audio_full_with_headers_and_item_fields(client, svc):
    _song(svc)
    resp = client.get(f"/api/maps/{MID}/audio")
    assert resp.status_code == 200 and resp.content == AUDIO
    assert resp.headers["content-type"] == "audio/ogg"
    assert resp.headers["cache-control"] == "private, max-age=86400"
    assert resp.headers["accept-ranges"] == "bytes" and resp.headers["etag"]
    item = client.get(f"/api/maps/{MID}").json()
    assert item["audio_url"] == f"/api/maps/{MID}/audio"
    assert item["preview_start"] is None or item["preview_start"] >= 0
    assert client.get("/api/maps").json()["items"][0] == item


def test_audio_preview_start_from_info(client, svc):
    _song(svc)
    info = svc.levels / NAME / "info.dat"
    text = info.read_text(encoding="utf-8")
    import re

    info.write_text(
        re.sub(r'"_previewStartTime"\s*:\s*[-\d.eE+]+', '"_previewStartTime": 12.5', text),
        encoding="utf-8",
    )
    assert client.get(f"/api/maps/{MID}").json()["preview_start"] == 12.5


def test_audio_range_206_and_416(client, svc):
    _song(svc)
    part = client.get(f"/api/maps/{MID}/audio", headers={"range": "bytes=10-19"})
    assert part.status_code == 206 and part.content == AUDIO[10:20]
    assert part.headers["content-range"] == f"bytes 10-19/{len(AUDIO)}"
    tail = client.get(f"/api/maps/{MID}/audio", headers={"range": "bytes=-5"})
    assert tail.status_code == 206 and tail.content == AUDIO[-5:]
    bad = client.get(f"/api/maps/{MID}/audio", headers={"range": f"bytes={len(AUDIO) + 5}-"})
    assert bad.status_code == 416
    assert client.get(f"/api/maps/{MID}/audio", headers={"range": "bytes=9-2"}).status_code == 416


@given(st.text(max_size=40))
def test_range_ok_never_raises(header):
    from saber_tooth.api.web_routes import _range_ok

    assert isinstance(_range_ok(header), bool)


@given(st.integers(0, 10**6), st.integers(0, 10**6))
def test_range_ok_rejects_exactly_inverted_pairs(a, b):
    from saber_tooth.api.web_routes import _range_ok

    assert _range_ok(f"bytes={a}-{b}") == (a <= b)


def test_audio_etag_304(client, svc):
    _song(svc)
    etag = client.get(f"/api/maps/{MID}/audio").headers["etag"]
    again = client.get(f"/api/maps/{MID}/audio", headers={"if-none-match": etag})
    assert again.status_code == 304 and again.content == b"" and again.headers["etag"] == etag


def test_audio_missing_is_404_and_null_url(client, svc):
    (svc.levels / NAME / "song.ogg").unlink()
    assert client.get(f"/api/maps/{MID}/audio").status_code == 404
    item = client.get(f"/api/maps/{MID}").json()
    assert item["audio_url"] is None and item["preview_start"] is None
    assert client.get("/api/maps/" + "f" * 12 + "/audio").status_code == 404


@pytest.mark.parametrize(
    "name",
    ["../secret.ogg", "..\\secret.ogg", "sub/s.ogg", "C:s.ogg", "song.txt", "song.dat", ".."],
)
def test_audio_name_escape_or_bad_extension_is_404(client, svc, name):
    (svc.levels.parent / "secret.ogg").write_bytes(b"secret")
    info = svc.levels / NAME / "info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace('"song.ogg"', f'"{name}"'), encoding="utf-8"
    )
    assert client.get(f"/api/maps/{MID}/audio").status_code == 404
    assert client.get(f"/api/maps/{MID}").json()["audio_url"] is None


def test_audio_symlink_out_of_folder_is_404(client, svc):
    outside = svc.levels.parent / "secret.ogg"
    outside.write_bytes(b"secret")
    song = svc.levels / NAME / "song.ogg"
    song.unlink()
    try:
        song.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    assert client.get(f"/api/maps/{MID}/audio").status_code == 404


@pytest.mark.parametrize(
    ("ext", "ctype"), [("egg", "audio/ogg"), ("wav", "audio/wav"), ("mp3", "audio/mpeg")]
)
def test_audio_content_types(client, svc, ext, ctype):
    (svc.levels / NAME / f"s.{ext}").write_bytes(AUDIO)
    info = svc.levels / NAME / "info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace('"song.ogg"', f'"s.{ext}"'), encoding="utf-8"
    )
    assert client.get(f"/api/maps/{MID}/audio").headers["content-type"] == ctype


def test_spa_routes_serve_index(web_client):
    client = web_client
    index = (client.web / "index.html").read_bytes()
    for path in (f"/maps/{MID}", "/maps/staging:abc", "/new"):
        resp = client.get(path)
        assert resp.status_code == 200 and resp.content == index
        assert resp.headers["content-type"].startswith("text/html")


def test_spa_does_not_shadow_api_mcp_or_static(web_client):
    client = web_client
    unknown = client.get("/api/nope")
    assert unknown.status_code == 404 and unknown.json() == {"error": "not found"}
    assert client.get("/api/maps/x/y/z").status_code == 404
    assert client.get("/mcp/nothing").status_code == 404
    assert client.get("/favicon.svg").headers["content-type"].startswith("image/svg")
    assert client.get("/maps/").status_code == 404 or client.get("/maps/").content != b""


@pytest.mark.parametrize("path", ["/maps/..%2F..%2Fpyproject.toml", "/%2e%2e/pyproject.toml",
                                  "/..%5Cpyproject.toml", "/new/../../pyproject.toml"])  # fmt: skip
def test_static_paths_cannot_leave_web_dir(client, path):
    resp = client.get(path)
    assert b"[project]" not in resp.content


def test_host_middleware_still_covers_new_routes(client):
    for path in (
        "/api/maps",
        f"/maps/{MID}",
        "/new",
        f"/api/maps/{MID}/cover",
        f"/api/maps/{MID}/audio",
    ):
        assert client.get(path, headers={"host": "evil.example"}).status_code == 403


def test_item_counts_approved_and_pending_proposals(client, svc):
    from tests.test_service import _propose

    assert client.get(f"/api/maps/{MID}").json()["pending"] == 0
    _propose(svc, MID, [], status="pending")
    _propose(svc, MID, [], status="approved")
    _propose(svc, MID, [], status="applied")
    item = client.get(f"/api/maps/{MID}").json()
    assert (item["approved"], item["pending"]) == (1, 1)
    assert client.get("/api/maps").json()["items"][0]["approved"] == 1


def test_every_web_file_is_served(web_client):
    for path in web_client.web.rglob("*"):
        if path.is_file():
            resp = web_client.get("/" + path.relative_to(web_client.web).as_posix())
            assert resp.status_code == 200 and resp.content == path.read_bytes(), path.name
