"""POST /api/maps/{id}/fix: the one-click fix job."""
# ruff: noqa: F811

from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from tests.test_api import MID, NAME, _wait, client, svc  # noqa: F401
from tests.test_fix_map import CLASH
from tests.test_service import _hashes, _make


def test_fix_job_writes_new_folder_and_reports(tmp_path):
    svc = _make(tmp_path, extra=CLASH)
    original = svc.levels / NAME
    before = _hashes(original)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        jid = http.post(f"/api/maps/{MID}/fix").json()["job"]
        job = _wait(http, jid)
        assert job["status"] == "done" and job["kind"] == "fix"
        report = job["result"]
        assert report["folder"] == f"{NAME} [saber-tooth]"
        assert report["fixed_id"] == map_id_for(report["folder"])
        assert report["errors"] == 0 and report["unfixed"] == []
        assert len(report["difficulties"]) == 5 and report["analysed"] is False
        assert set(report) >= {"before", "after", "rounds", "applied"}
        assert _hashes(original) == before
        folders = {m["folder"] for m in http.get("/api/maps").json()["items"]}
        assert report["folder"] in folders


def test_fixed_copy_lists_as_scanned_and_links_from_original(tmp_path):
    svc = _make(tmp_path, extra=CLASH)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        jid = http.post(f"/api/maps/{MID}/fix").json()["job"]
        report = _wait(http, jid)["result"]
        items = {m["id"]: m for m in http.get("/api/maps").json()["items"]}
        assert MID not in items  # original hidden once its copy exists
        copy = items[report["fixed_id"]]
        assert copy["status"] == "ok" and copy["errors"] == 0 and copy["warnings"] == 0
        assert copy["scanned_at"] and copy["pending"] == 0
        original = http.get(f"/api/maps/{MID}").json()
        assert original["fixed_copy_id"] == report["fixed_id"]
        assert original["fixed_copy_folder"] == report["folder"]
        assert copy["fixed_copy_id"] is None and copy["original_id"] == MID


def test_fix_unreadable_map_is_409(client, svc):
    svc.store.upsert_map("b" * 12, "Broken", "Broken", "", "", "bad json")
    resp = client.post(f"/api/maps/{'b' * 12}/fix")
    assert resp.status_code == 409 and "error" in resp.json()


def test_fix_unknown_map_is_404(client):
    resp = client.post(f"/api/maps/{'0' * 12}/fix")
    assert resp.status_code == 404 and "error" in resp.json()


# Moved from test_api.py, which sits at the 300-line cap; the copy link fields are optional.
def test_list_maps_has_ui_fields(client):
    page = client.get("/api/maps").json()
    rows = page["items"]
    assert (page["total"], page["offset"], page["limit"]) == (1, 0, 40) and len(rows) == 1
    links = {"fixed_copy_id", "fixed_copy_folder", "original_id", "original_folder"}
    assert set(rows[0]) - links == {
        "id", "folder", "title", "mapper", "environment", "parse_error", "errors", "warnings",
        "scanned_at", "status", "cover_url", "difficulties", "approved", "pending",
    } | {"bpm", "duration_s", "job", "audio_url", "preview_start"}  # fmt: skip
    assert rows[0]["id"] == MID and rows[0]["folder"] == NAME
