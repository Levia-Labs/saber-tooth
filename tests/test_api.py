import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from saber_tooth import api as api_module
from saber_tooth.api import create_app
from saber_tooth.fixer import Flip
from saber_tooth.model import Cut
from saber_tooth.service import map_id_for
from tests.test_service import NAME, NOTE, _make, _propose

MID = map_id_for(NAME)
STAGING = "staging:" + "a" * 32


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


@pytest.fixture
def client(svc):
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        yield c


def _wait(client, job_id: str) -> dict:
    for _ in range(200):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_import_does_not_touch_levels():
    assert "app" not in vars(api_module)


def test_list_maps_has_ui_fields(client):
    page = client.get("/api/maps").json()
    rows = page["items"]
    assert (page["total"], page["offset"], page["limit"]) == (1, 0, 40) and len(rows) == 1
    assert set(rows[0]) == {
        "id", "folder", "title", "mapper", "environment", "parse_error", "errors", "warnings",
        "scanned_at", "status", "cover_url", "difficulties", "approved", "pending",
    } | {"bpm", "duration_s", "job"}  # fmt: skip
    assert rows[0]["id"] == MID and rows[0]["folder"] == NAME


def test_scan_job_and_proposals(client):
    started = client.post(f"/api/maps/{MID}/scan")
    assert started.status_code == 200
    job = _wait(client, started.json()["job"])
    assert job["status"] == "done" and job["kind"] == "scan"
    assert set(job["result"]) == {"map_id", "proposals", "analysis"}
    assert client.get("/api/maps").json()["items"][0]["errors"] >= 0
    assert isinstance(client.get(f"/api/maps/{MID}/proposals").json(), list)


def test_approve_reject_and_approve_all(client, svc):
    a = _propose(svc, MID, [Flip("Hard", NOTE, Cut(0))], status="pending")
    b = _propose(svc, MID, [], status="pending")
    assert client.post(f"/api/proposals/{a}/approve").json() == {"id": a, "status": "approved"}
    rows = {p["id"]: p for p in client.get(f"/api/maps/{MID}/proposals").json()}
    assert rows[a]["status"] == "approved" and "ops" not in rows[a]
    assert set(rows[a]) == {
        "id", "rule", "difficulty", "severity", "summary", "status", "before", "after",
        "walls_before", "walls_after", "walls_context",
    }  # fmt: skip
    assert client.post(f"/api/proposals/{a}/reject").json()["status"] == "rejected"
    assert client.post(f"/api/maps/{MID}/approve-all").json() == {"approved": 1}
    assert svc.store.proposals(MID)[1]["id"] == b
    assert svc.store.proposals(MID)[1]["status"] == "approved"
    assert svc.store.proposals(MID)[0]["status"] == "rejected"


def test_apply_job_done_and_conflict(client, svc):
    _propose(svc, MID, [Flip("Hard", NOTE, Cut(0))])
    job = _wait(client, client.post(f"/api/maps/{MID}/apply").json()["job"])
    assert job["status"] == "done" and set(job["result"]) == {"map_id", "folder"}
    assert (svc.levels / job["result"]["folder"]).is_dir()
    again = _wait(client, client.post(f"/api/maps/{MID}/apply").json()["job"])
    assert again["status"] == "failed" and again["error"]


def test_apply_conflict_result_lists_ids(client, svc):
    pid = _propose(svc, MID, [Flip("Hard", NOTE, Cut(0)), Flip("Hard", NOTE, Cut(1))])
    job = _wait(client, client.post(f"/api/maps/{MID}/apply").json()["job"])
    assert job["status"] == "failed"
    assert job["result"] == {"conflict": [pid]}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/maps/{m}/scan"),
        ("get", "/api/maps/{m}/proposals"),
        ("post", "/api/maps/{m}/approve-all"),
        ("post", "/api/maps/{m}/apply"),
        ("post", "/api/proposals/999/approve"),
        ("post", "/api/proposals/999/reject"),
        ("post", "/api/proposals/abc/approve"),
        ("get", "/api/jobs/{j}"),
        ("get", "/api/jobs/not-a-job-id"),
    ],
)
def test_unknown_ids_are_404(client, method, path):
    url = path.format(m="0" * 12, j="f" * 32)
    resp = getattr(client, method)(url)
    assert resp.status_code == 404 and "error" in resp.json()


def test_malformed_and_staging_ids(client):
    assert client.get("/api/maps/..%2F..%2Fetc/proposals").status_code == 404
    assert client.post(f"/api/maps/{STAGING}/scan").status_code == 404
    assert client.get(f"/api/maps/{STAGING}/proposals").status_code == 404


def test_unreadable_map_scan_is_409(client, svc):
    svc.store.upsert_map("b" * 12, "Broken", "Broken", "", "", "bad json")
    resp = client.post(f"/api/maps/{'b' * 12}/scan")
    assert resp.status_code == 409 and "error" in resp.json()


def test_generate_url_job(client, svc, monkeypatch):
    seen = []
    monkeypatch.setattr(
        svc, "run_generate", lambda u: seen.append(u) or {"map_id": "m", "proposal": 1}
    )
    resp = client.post("/api/generate", json={"url": "https://youtu.be/abc"})
    job = _wait(client, resp.json()["job"])
    assert job["status"] == "done" and job["result"]["proposal"] == 1
    assert seen == ["https://youtu.be/abc"]


BAD_URLS = [
    "/etc/passwd", "file:///x", "ftp://youtube.com/x", "http://127.0.0.1/x",
    "http://169.254.169.254/latest", "https://youtube.com.evil.com/watch?v=1",
    "https://youtube.com" + "@evil.com/", "https://evil.com" + chr(92) + "@youtube.com/",
    "https://evil.com/youtube.com",
    "https://youtube.com:99999/", "https://notyoutube.com/", "https://x.youtube.com/", "",
]  # fmt: skip


@pytest.mark.parametrize("body", [*({"url": u} for u in BAD_URLS), {"x": 1}, [1], {"url": 5}])
def test_generate_rejects_non_youtube(client, body):
    resp = client.post("/api/generate", json=body)
    assert resp.status_code == 400
    assert resp.json() == {"error": "only YouTube URLs are supported"}


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com/watch?v=1", "http://www.youtube.com/watch?v=1",
        "https://m.youtube.com/watch?v=1", "https://music.youtube.com/watch?v=1",
        "https://youtu.be/abc", "https://YouTube.com./watch?v=1", "https://www.youtube.com:443/x",
    ],
)  # fmt: skip
def test_generate_allows_youtube_hosts(client, svc, monkeypatch, url):
    monkeypatch.setattr(svc, "run_generate", lambda u: {"map_id": "m", "proposal": 1})
    assert "job" in client.post("/api/generate", json={"url": url}).json()


def test_generate_bad_json(client):
    resp = client.post("/api/generate", content=b"{", headers={"content-type": "application/json"})
    assert resp.status_code == 400


def test_generate_multipart_stores_under_data(client, svc, monkeypatch):
    seen = []

    def fake(path):
        seen.append((Path(path), Path(path).read_bytes()))
        return {"map_id": "m", "proposal": 1}

    monkeypatch.setattr(svc, "run_generate", fake)
    files = {"file": ("../../evil name.MP3", b"abc", "audio/mpeg")}
    job = _wait(client, client.post("/api/generate", files=files).json()["job"])
    assert job["status"] == "done"
    path, data = seen[0]
    assert data == b"abc" and path.suffix == ".mp3"
    assert path.parent.parent == svc.data / "uploads" and path.name == "evil-name.mp3"
    assert not path.parent.exists()


def test_generate_multipart_rejects_bad_type_and_missing_file(client):
    bad = client.post("/api/generate", files={"file": ("a.exe", b"x")})
    assert bad.status_code == 415
    other = client.post("/api/generate", files={"other": ("a.mp3", b"x")})
    assert other.status_code == 400


def test_generate_multipart_too_large_is_413(client, svc, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    big = b"0" * (2 * 1024 * 1024)
    resp = client.post("/api/generate", files={"file": ("a.wav", big)})
    assert resp.status_code == 413 and "error" in resp.json()
    assert not list(svc.data.glob("uploads/*"))


def test_generate_multipart_stream_over_limit_without_length(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    boundary = "xx"
    head = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n\r\n'

    def body():
        yield head.encode()
        for _ in range(40):
            yield b"0" * 65536
        yield f"\r\n--{boundary}--\r\n".encode()

    resp = client.post(
        "/api/generate",
        content=body(),
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )
    assert resp.status_code == 413


def test_foreign_origin_post_is_403(client):
    resp = client.post("/api/lightshow/learn", headers={"origin": "http://evil.example"})
    assert resp.status_code == 403 and "error" in resp.json()
    assert client.post("/api/maps/x/scan", headers={"origin": "null"}).status_code == 403


def test_same_and_absent_origin_allowed(client, svc):
    ok = client.post("/api/lightshow/learn", headers={"origin": "http://localhost"})
    assert ok.status_code == 200
    resp = client.get("/api/maps", headers={"origin": "http://evil.example"})
    assert resp.status_code == 200 and "access-control-allow-origin" not in resp.headers


def test_learn_job(client):
    job = _wait(client, client.post("/api/lightshow/learn").json()["job"])
    assert job["status"] == "done" and "units" in job["result"]


def test_static_frontend(client):
    assert "saber-tooth" in client.get("/").text.lower()
    assert client.get("/favicon.svg").status_code == 200
    assert client.get("/app.js").status_code == 200


def test_staged_proposal_view_hides_path(client, svc, tmp_path):
    token = "c" * 32
    staging = svc.data / "staging" / token
    staging.mkdir(parents=True)
    p = {
        "rule": "create-map", "difficulty": "*", "severity": "warn", "summary": "s", "ops": [],
        "before": [], "after": {"staging": str(staging), "title": "t"},
    }  # fmt: skip
    svc.store.add_proposals(f"staging:{token}", [p])
    rows = client.get(f"/api/maps/staging:{token}/proposals").json()
    assert rows[0]["difficulty"] == "Expert" and rows[0]["after"] == []
    assert str(staging) not in str(rows)


def test_applied_proposal_cannot_be_reopened(client, svc):
    pid = _propose(svc, MID, [], status="applied")
    for verb in ("approve", "reject"):
        resp = client.post(f"/api/proposals/{pid}/{verb}")
        assert resp.status_code == 409 and resp.json() == {"error": "proposal already applied"}
    assert svc.store.proposal(pid)["status"] == "applied"


@pytest.mark.parametrize("origin", ["https://localhost", "http://localhost:8100"])
def test_origin_scheme_or_port_mismatch_is_403(client, origin):
    assert client.post("/api/lightshow/learn", headers={"origin": origin}).status_code == 403


def test_maps_refresh_when_levels_listing_changes(client, svc):
    assert client.get("/api/maps").json()["total"] == 1
    shutil.copytree(svc.levels / NAME, svc.levels / "Second")
    assert {m["folder"] for m in client.get("/api/maps").json()["items"]} == {NAME, "Second"}
    shutil.rmtree(svc.levels / "Second")
    assert [m["folder"] for m in client.get("/api/maps").json()["items"]] == [NAME]


def test_upload_title_is_sanitised_filename_stem(svc):
    from saber_tooth.analyser_client import AnalyserError

    seen = []

    class Client:
        uploads = None

        def analyse_file(self, path, name):
            seen.append(name)
            raise AnalyserError("stop")

    svc.client = Client()
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        files = {"file": ("dir/My Song (v2)!.flac", b"abc")}
        job = _wait(c, c.post("/api/generate", files=files).json()["job"])
    assert job["status"] == "failed" and seen == ["My-Song-v2.flac"]
