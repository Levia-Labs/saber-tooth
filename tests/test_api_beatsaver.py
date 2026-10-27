# ruff: noqa: F811
import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.beatsaver.client import BeatSaverClient
from tests.test_api import MID, _wait, svc  # noqa: F401

FIX = Path(__file__).parent / "fixtures" / "beatsaver"
MAPS = Path(__file__).parent / "fixtures" / "maps" / "v2_basic"
HITS = "diffs=Easy,Normal,Hard"


def fixture(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def map_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for p in MAPS.iterdir():
            z.writestr(p.name, p.read_bytes())
    return buf.getvalue()


class Upstream:
    """Fake BeatSaver: serves the fixtures and records the requests."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.limited_from: int | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.url.host.startswith("r2cdn"):
            return httpx.Response(200, content=map_zip())
        if path.startswith("/search/text/"):
            page = int(path.rsplit("/", 1)[1])
            if self.limited_from is not None and page >= self.limited_from:
                return httpx.Response(429, headers={"retry-after": "30"})
            return httpx.Response(
                200, json=fixture("search_page0.json") if page == 0 else {"docs": []}
            )
        if path.startswith("/maps/ids/"):
            wanted = path.rsplit("/", 1)[1].split(",")
            docs = {d["id"]: d for d in fixture("search_page0.json")["docs"] if d["id"] in wanted}
            return httpx.Response(200, json=docs)
        if path.startswith("/playlists/search/"):
            return httpx.Response(200, json=fixture("playlist_search.json"))
        if path.startswith("/playlists/id/77/"):
            body = fixture("playlist_page0.json") if path.endswith("/0") else {"maps": []}
            return httpx.Response(200, json=body)
        return httpx.Response(404, json={})


def make_app(svc, upstream, playlists=None):
    bs = BeatSaverClient(httpx.MockTransport(upstream), sleep=lambda s: None)
    return create_app(svc, bs_client=bs, playlists_dir=playlists)


@pytest.fixture
def upstream():
    return Upstream()


@pytest.fixture
def bs(svc, upstream):
    with TestClient(make_app(svc, upstream), base_url="http://localhost") as c:
        yield c


def test_search_item_shape_and_filters(bs):
    page = bs.get(f"/api/beatsaver/search?{HITS}&min_rating=0.95").json()
    assert [i["id"] for i in page["items"]] == ["3a1f4"]
    assert page["scanned"] == 2 and page["matched"] == 1 and page["cursor"] is None
    assert "partial" not in page
    item = page["items"][0]
    assert set(item) == {
        "id", "name", "song", "mapper", "cover_url", "preview_url", "bpm", "duration",
        "rating", "upvotes", "downvotes", "tags", "ranked", "difficulties", "installed",
        "library_id",
    }  # fmt: skip
    assert item["song"] == "Neon Pulse" and item["rating"] == 0.9712 and item["duration"] == 214
    assert [d["difficulty"] for d in item["difficulties"]] == ["Easy", "Normal", "Hard"]
    assert item["difficulties"][0] == {"difficulty": "Easy", "nps": 0.9, "njs": 10.0}
    assert item["installed"] is False and item["library_id"] is None
    assert item["cover_url"].startswith("https://eu.cdn.beatsaver.com/")
    first = bs.get("/api/beatsaver/search?limit=1").json()
    assert [m["id"] for m in first["items"]] == ["3a1f4"] and first["cursor"] == "0.1"
    second = bs.get("/api/beatsaver/search?limit=1&cursor=0.1").json()
    assert [m["id"] for m in second["items"]] == ["3a1f5"] and second["cursor"] == "1.0"


def test_search_sends_server_filters(bs, upstream):
    bs.get("/api/beatsaver/search?tags=rock,metal&min_rating=0.9&order=Latest&ranked=true&limit=5")
    req = upstream.requests[0]
    assert req.url.params["tags"] == "rock|metal" and req.url.params["minRating"] == "0.9"
    assert req.url.params["order"] == "Latest" and req.url.params["leaderboard"] == "Ranked"
    assert "minNps" not in req.url.params


def test_nps_filter_runs_locally(bs):
    hit = bs.get("/api/beatsaver/search?nps_min=1&nps_max=2").json()
    assert [i["id"] for i in hit["items"]] == ["3a1f4"]
    none = bs.get("/api/beatsaver/search?nps_min=1&nps_max=2&nps_scope=all").json()
    assert none["items"] == [] and none["scanned"] == 2


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "limit=x",
        "min_rating=2",
        "min_rating=nan",
        "nps_min=-1",
        "nps_max=31",
        "nps_min=3&nps_max=1",
        "nps_scope=some",
        "diffs=Impossible",
        "diffs_mode=most",
        "order=Random2",
        "ascending=maybe",
        "from=2025-13-01",
        "from=yesterday",
        "bpm_max=5000",
        "duration_min=9999",
        "cursor=abc",
        "cursor=1.-1",
        "tags=a;b",
        "q=" + "a" * 201,
        "tags=" + ",".join(str(i) for i in range(40)),
    ],
)
def test_bad_params_are_400(bs, query):
    resp = bs.get(f"/api/beatsaver/search?{query}")
    assert resp.status_code == 400 and "error" in resp.json()


def test_rate_limited_search_returns_partial(svc, upstream):
    upstream.limited_from = 1
    with TestClient(make_app(svc, upstream), base_url="http://localhost") as c:
        resp = c.get(f"/api/beatsaver/search?{HITS}")
        assert resp.status_code == 200
        body = resp.json()
        assert [i["id"] for i in body["items"]] == ["3a1f4"]
        assert body["partial"] is True and body["retry_after"] == 30 and body["cursor"] == "1.0"
        nothing = c.get(f"/api/beatsaver/search?{HITS}&cursor=1.0&q=other")
        assert nothing.status_code == 429
        assert nothing.json()["retry_after"] == 30 and nothing.headers["retry-after"] == "30"


def test_installed_flag_by_key_hash_and_folder(bs, svc):
    svc.store.set_bs(MID, "3a1f4", "")
    item = bs.get(f"/api/beatsaver/search?{HITS}").json()["items"][0]
    assert item["installed"] is True and item["library_id"] == MID
    svc.store.set_bs(MID, "other", "aabbccddeeff00112233445566778899aabbccdd")
    assert bs.get("/api/beatsaver/maps/3a1f4").json()["library_id"] == MID


def test_map_route(bs):
    assert bs.get("/api/beatsaver/maps/3a1f4").json()["name"] == "Neon Pulse"
    assert bs.get("/api/beatsaver/maps/ffff").status_code == 404
    assert bs.get("/api/beatsaver/maps/..%2Fx").status_code == 404


def test_playlists(bs):
    found = bs.get("/api/beatsaver/playlists/search?q=chill").json()
    assert found["items"] == [
        {
            "id": "77", "name": "Chill Electronic", "owner": "curator",
            "cover_url": "https://cdn.beatsaver.com/playlist/77.png", "map_count": 2,
        }
    ]  # fmt: skip
    assert found["cursor"] == "1"
    page = bs.get(f"/api/beatsaver/playlists/77?{HITS}").json()
    assert page["playlist"]["name"] == "Chill Electronic"
    assert (
        page["scanned"] == 2 and page["items"] == []
    )  # fixture playlist maps list no difficulties
    all_maps = bs.get("/api/beatsaver/playlists/77").json()
    assert [i["id"] for i in all_maps["items"]] == ["3a1f4", "3a1f5"]
    assert bs.get("/api/beatsaver/playlists/abc").status_code == 404
    assert bs.get("/api/beatsaver/playlists/search?cursor=x").status_code == 400


def test_download_job_installs_and_skips(bs, svc):
    started = bs.post("/api/beatsaver/download", json={"ids": ["3a1f4", "3A1F4", "ffff"]})
    assert started.status_code == 200
    job = _wait(bs, started.json()["job"])
    assert job["status"] == "done" and job["kind"] == "bs-download"
    results = {r["id"]: r for r in job["result"]["results"]}
    assert len(results) == 2
    assert results["3a1f4"]["status"] == "installed"
    assert results["3a1f4"]["folder"] == "3a1f4 (Neon Pulse - pulsewright)"
    assert results["ffff"]["status"] == "failed" and results["ffff"]["reason"]
    assert (svc.levels / results["3a1f4"]["folder"] / "song.ogg").is_file()
    items = bs.get(f"/api/beatsaver/search?{HITS}").json()["items"]
    assert items[0]["installed"] is True and items[0]["library_id"]
    library = {m["folder"] for m in bs.get("/api/maps?limit=100").json()["items"]}
    assert "3a1f4 (Neon Pulse - pulsewright)" in library
    second = _wait(bs, bs.post("/api/beatsaver/download", json={"ids": ["3a1f4"]}).json()["job"])
    assert second["result"]["results"][0]["status"] == "skipped"


def test_installed_via_original_folder_untouched(bs, svc):
    before = sorted(p.name for p in svc.levels.iterdir())
    _wait(bs, bs.post("/api/beatsaver/download", json={"ids": ["3a1f4"]}).json()["job"])
    after = sorted(p.name for p in svc.levels.iterdir())
    assert set(before) < set(after) and len(after) == len(before) + 1


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"ids": [f"{i:x}" for i in range(101)]}, 413),
        ({"ids": []}, 400),
        ({"ids": ["../x"]}, 400),
        ({"ids": [1]}, 400),
        ({"ids": "3a1f4"}, 400),
        ({}, 400),
        ([], 400),
    ],
)
def test_download_validation(bs, body, status):
    assert bs.post("/api/beatsaver/download", json=body).status_code == status


def test_download_rejects_non_json(bs):
    assert bs.post("/api/beatsaver/download", content=b"nope").status_code == 400


def test_exactly_100_ids_accepted(bs):
    ids = [f"{i:x}" for i in range(100)]
    assert bs.post("/api/beatsaver/download", json={"ids": ids}).status_code == 200
