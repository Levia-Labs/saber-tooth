"""POST /api/maps/{id}/fix: the one-click fix job."""
# ruff: noqa: F811

from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from tests.test_api import MID, NAME, _wait, client, svc  # noqa: F401
from tests.test_fix_map import CLASH
from tests.test_service import _hashes, _make


def test_fix_job_writes_new_folder_and_reports(tmp_path):
    svc = _make(tmp_path, extra=CLASH)
    original = svc.levels / NAME
    before = _hashes(original)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        jid = http.post(f"/api/maps/{MID}/fix").json()["job"]
        job = _wait(client, jid)
        assert job["status"] == "done" and job["kind"] == "fix"
        report = job["result"]
        assert report["folder"] == f"{NAME} [saber-tooth]"
        assert report["errors"] == 0 and report["unfixed"] == []
        assert len(report["difficulties"]) == 5 and report["analysed"] is False
        assert set(report) >= {"before", "after", "rounds", "applied"}
        assert _hashes(original) == before
        folders = {m["folder"] for m in http.get("/api/maps").json()["items"]}
        assert report["folder"] in folders


def test_fix_unreadable_map_is_409(client, svc):
    svc.store.upsert_map("b" * 12, "Broken", "Broken", "", "", "bad json")
    resp = client.post(f"/api/maps/{'b' * 12}/fix")
    assert resp.status_code == 409 and "error" in resp.json()


def test_fix_unknown_map_is_404(client):
    resp = client.post(f"/api/maps/{'0' * 12}/fix")
    assert resp.status_code == 404 and "error" in resp.json()
