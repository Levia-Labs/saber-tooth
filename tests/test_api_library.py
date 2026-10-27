# ruff: noqa: F811
import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.api.library import MAX_COVER_BYTES, parse_query
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
    for path in ("/api/maps", f"/maps/{MID}", "/new", f"/api/maps/{MID}/cover"):
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
