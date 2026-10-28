# ruff: noqa: F811
import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from tests.crop_helpers import NAME, cuts, make_360, make_service  # noqa: F401
from tests.test_api import _wait
from tests.test_service import _hashes

MID = map_id_for(NAME)


@pytest.fixture
def http(tmp_path):
    svc = make_service(tmp_path)
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        c.svc = svc
        yield c


def test_timeline_route_returns_the_contract(http):
    body = http.get(f"/api/maps/{MID}/timeline").json()
    assert body["map_id"] == MID and set(body["lengths"]) == {"60", "120"}
    assert body["lengths"]["60"]["suggestions"][0]["end_kind"] in {
        "section",
        "phrase",
        "bar4",
        "bar",
    }
    assert body["map_only"] is True and body["min_length_s"] == 1.0


def test_timeline_for_an_unknown_map_is_404(http):
    assert http.get(f"/api/maps/{'0' * 12}/timeline").status_code == 404
    assert http.get("/api/maps/not-an-id/timeline").status_code == 404


def test_timeline_for_an_unreadable_map_is_409(http):
    http.svc.store.upsert_map("b" * 12, "Broken", "Broken", "", "", "bad json")
    assert http.get(f"/api/maps/{'b' * 12}/timeline").status_code == 409


def test_timeline_without_standard_notes_is_422(http):
    make_360(http.svc.levels / NAME)
    resp = http.get(f"/api/maps/{MID}/timeline")
    assert resp.status_code == 422 and "no Standard difficulty has notes" in resp.json()["error"]


def test_crop_job_writes_a_new_folder(http, cuts):
    original = http.svc.levels / NAME
    before = _hashes(original)
    window = http.get(f"/api/maps/{MID}/timeline").json()["lengths"]["60"]["suggestions"][0]
    body = {"start_beat": window["start_beat"], "end_beat": window["end_beat"]}
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=body).json()["job"])
    assert job["status"] == "done" and job["kind"] == "crop"
    assert job["result"]["folder"] == "Song [1 min]"
    assert job["result"]["cropped_id"] == map_id_for("Song [1 min]")
    assert _hashes(original) == before
    folders = {m["folder"] for m in http.get("/api/maps").json()["items"]}
    assert "Song [1 min]" in folders


@pytest.mark.parametrize(
    ("body", "rule"),
    [
        ({"start_beat": "x", "end_beat": 3}, "start_beat must be a number"),
        ({"start_beat": 0, "end_beat": None}, "end_beat must be a number"),
        ({"start_beat": True, "end_beat": 3}, "start_beat must be a number"),
        ({"start_beat": -1, "end_beat": 3}, "start_beat must be a number"),
        ({"start_beat": 8, "end_beat": 8}, "end_beat must be after start_beat"),
        ({"start_beat": 5, "end_beat": 6.8}, "the window must be at least 1 second long"),
        ({"start_beat": 0, "end_beat": 9000}, "the window must lie inside the song"),
        ({"start_beat": 200, "end_beat": 400}, "the window must lie inside the song"),
        ([], "send either start_beat and end_beat or start_s and end_s"),
    ],
)
def test_crop_422_names_the_rule(http, body, rule):
    resp = http.post(f"/api/maps/{MID}/crop", json=body)
    assert resp.status_code == 422 and rule in resp.json()["error"]


def test_crop_with_a_body_that_is_not_json_is_400(http):
    resp = http.post(f"/api/maps/{MID}/crop", content=b"nope")
    assert resp.status_code == 400


def test_crop_is_409_while_the_map_has_a_running_job(http):
    http.svc.store.create_job("scan", MID)
    resp = http.post(f"/api/maps/{MID}/crop", json={"start_beat": 0, "end_beat": 128})
    assert resp.status_code == 409


def test_crop_of_an_unknown_map_is_404(http):
    resp = http.post(f"/api/maps/{'0' * 12}/crop", json={"start_beat": 0, "end_beat": 128})
    assert resp.status_code == 404


def test_crop_with_a_huge_integer_is_422(http):
    raw = b'{"start_beat": 1' + b"0" * 400 + b', "end_beat": 128}'
    resp = http.post(
        f"/api/maps/{MID}/crop", content=raw, headers={"content-type": "application/json"}
    )
    assert resp.status_code == 422 and "start_beat must be a number" in resp.json()["error"]


def test_crop_accepts_a_free_mid_bar_window(http, cuts):
    body = {"start_beat": 5.5, "end_beat": 71.25}
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=body).json()["job"])
    assert job["status"] == "done" and job["result"]["folder"] == "Song [crop 0m33s]"


def test_crop_rejects_a_window_under_a_second(http):
    resp = http.post(f"/api/maps/{MID}/crop", json={"start_beat": 5.0, "end_beat": 6.8})
    assert resp.status_code == 422 and "at least 1 second" in resp.json()["error"]


def _tempo_change_http(tmp_path):
    from saber_tooth.model import BpmEvent
    from tests.crop_helpers import stepped_map

    bm = stepped_map()
    for d in bm.difficulties.values():
        d.bpm_events = [BpmEvent(64.0, 60.0)]  # 120 bpm for 32 s, then 1 beat per second
    return make_service(tmp_path, bm)


def test_crop_by_seconds_converts_with_the_bpm_changes(tmp_path, cuts):
    with TestClient(create_app(_tempo_change_http(tmp_path)), base_url="http://localhost") as c:
        body = {"start_s": 40.0, "end_s": 50.0}
        job = _wait(c, c.post(f"/api/maps/{MID}/crop", json=body).json()["job"])
        assert job["status"] == "done"
        assert job["result"]["start_beat"] == pytest.approx(72.0)
        assert job["result"]["end_beat"] == pytest.approx(82.0)


@pytest.mark.parametrize(
    ("body", "rule"),
    [
        (
            {"start_beat": 0, "end_beat": 128, "start_s": 0, "end_s": 60},
            "send either start_beat and end_beat or start_s and end_s",
        ),
        ({}, "send either start_beat and end_beat or start_s and end_s"),
        ({"start_s": 5}, "end_s must be a number"),
        ({"start_beat": 5, "end_s": 9}, "send either start_beat and end_beat or start_s and end_s"),
        ({"start_s": "x", "end_s": 9}, "start_s must be a number"),
        ({"start_s": 3, "end_s": 3.5}, "the window must be at least 1 second long"),
        ({"start_s": 0, "end_s": 99999}, "the window must lie inside the song"),
    ],
)
def test_crop_seconds_pair_rules(http, body, rule):
    resp = http.post(f"/api/maps/{MID}/crop", json=body)
    assert resp.status_code == 422 and rule in resp.json()["error"]


def test_crop_an_exact_one_second_window_across_a_tempo_change_is_accepted(tmp_path, cuts):
    with TestClient(create_app(_tempo_change_http(tmp_path)), base_url="http://localhost") as c:
        for start in (10.0, 31.7, 32.3, 40.1):
            body = {"start_s": start, "end_s": start + 1.0}
            resp = c.post(f"/api/maps/{MID}/crop", json=body)
            assert resp.status_code == 200, (start, resp.json())
            assert _wait(c, resp.json()["job"])["status"] == "done"
