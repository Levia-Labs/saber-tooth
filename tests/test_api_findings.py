"""GET /api/maps/{id}/findings lists the scan's findings, with their proposal when one exists."""

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from tests.test_service import NAME, _make

MID = map_id_for(NAME)
FINDING = {
    "rule": "flip-cut",
    "difficulty": "Hard",
    "beat_start": 8.0,
    "beat_end": 8.0,
    "severity": "error",
    "message": "hand flips",
    "notes": [],
    "walls": [],
}


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


@pytest.fixture
def client(svc):
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        yield c


def _scan(svc, findings, proposals=()):
    svc.store.replace_open_proposals(MID, list(proposals), {"findings": findings, "analysis": None})


def test_unscanned_map_reports_scanned_false(svc, client):
    assert svc.store.scan_info(MID) is None
    body = client.get(f"/api/maps/{MID}/findings").json()
    assert body == {"scanned": False, "findings": []}


def test_finding_without_a_proposal_is_listed_with_no_proposal_id(svc, client):
    _scan(svc, [FINDING])
    body = client.get(f"/api/maps/{MID}/findings").json()
    assert body["scanned"] is True
    [f] = body["findings"]
    assert (f["rule"], f["severity"], f["difficulty"], f["message"]) == (
        "flip-cut",
        "error",
        "Hard",
        "hand flips",
    )
    assert f["proposal_id"] is None
    assert "notes" not in f


def test_finding_with_a_proposal_carries_its_id(svc, client):
    prop = {
        "rule": "flip-cut",
        "difficulty": "Hard",
        "severity": "error",
        "summary": "s",
        "ops": [],
        "before": [],
        "after": [],
        "finding": FINDING,
    }
    _scan(svc, [FINDING], [prop])
    [f] = client.get(f"/api/maps/{MID}/findings").json()["findings"]
    assert f["proposal_id"] == client.get(f"/api/maps/{MID}/proposals").json()[0]["id"]


def test_unknown_map_is_404(client):
    assert client.get("/api/maps/" + "0" * 12 + "/findings").status_code == 404
