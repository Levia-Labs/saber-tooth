import threading
import time

import pytest
from fastapi.testclient import TestClient

from saber_tooth import api as api_module
from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from tests.test_service import NAME, _make


@pytest.fixture
def api(tmp_path, monkeypatch):
    made = []
    real = api_module.Api

    def capture(service):
        made.append(real(service))
        return made[0]

    monkeypatch.setattr(api_module, "Api", capture)
    api = {}
    api["svc"] = _make(tmp_path)
    api["app"] = create_app(api["svc"])
    return made[0], api["app"]


@pytest.fixture
def client(api):
    with TestClient(api[1], base_url="http://localhost") as c:
        yield c


@pytest.fixture
def jobs_api(api):
    return api[0]


@pytest.fixture
def a_map_id(client, jobs_api):
    client.get("/api/maps")  # indexes the library
    mid = map_id_for(NAME)
    assert jobs_api.store.get_map(mid)
    return mid


@pytest.fixture
def gate(jobs_api):
    gate = threading.Event()
    jobs_api.jobs.register("block", lambda args, progress: gate.wait(5))
    yield gate
    gate.set()


def claimed(api, job_id: str) -> None:
    """Block until the worker has claimed the job (status running), 5 s at most."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if api.store.job(job_id)["status"] == "running":
            return
        time.sleep(0.01)
    raise AssertionError("worker never claimed the job")


def test_list_shape_positions_and_titles(client, jobs_api, gate) -> None:
    api = jobs_api
    running = api.jobs.submit("block")
    claimed(api, running)
    q1 = api.jobs.submit("block")
    q2 = api.jobs.submit("generate", {"url": "https://youtu.be/x"})
    body = client.get("/api/jobs").json()
    assert [j["id"] for j in body["running"]] == [running]
    assert [(j["id"], j["position"]) for j in body["queued"]] == [(q1, 1), (q2, 2)]
    assert body["queued"][1]["title"] == "Generate from YouTube"
    assert body["running"][0]["position"] is None
    assert set(body) == {"running", "queued", "recent"}
    assert "args" not in body["queued"][1] and "result" not in body["queued"][1]


def test_title_is_the_map_title_or_a_kind_label(client, jobs_api, gate, a_map_id) -> None:
    api = jobs_api
    blocker = api.jobs.submit("block")
    claimed(api, blocker)
    job = api.jobs.submit("scan", {"map_id": a_map_id}, map_id=a_map_id)
    learn = api.jobs.submit("learn")
    queued = {j["id"]: j for j in client.get("/api/jobs").json()["queued"]}
    assert queued[job]["title"] == api.store.get_map(a_map_id)["title"]
    assert queued[job]["map_exists"] is True
    assert queued[learn]["title"] == "Learn lightshows"


def test_detail_has_the_new_fields(client, jobs_api, gate) -> None:
    api = jobs_api
    blocker = api.jobs.submit("block")
    claimed(api, blocker)
    waiting = api.jobs.submit("block")
    body = client.get(f"/api/jobs/{waiting}").json()
    assert body["status"] == "queued" and body["position"] == 1
    for key in ("result", "started_at", "progress", "progress_at", "title", "map_id"):
        assert key in body


def test_cancel_status_codes(client, jobs_api, gate) -> None:
    api = jobs_api
    running = api.jobs.submit("block")
    claimed(api, running)
    waiting = api.jobs.submit("block")
    assert client.delete(f"/api/jobs/{waiting}").json()["status"] == "cancelled"
    r = client.delete(f"/api/jobs/{running}")
    assert r.status_code == 200 and r.json()["cancel_requested"] is True
    gate.set()
    api.jobs.wait(running)
    r = client.delete(f"/api/jobs/{running}")
    assert r.status_code == 409 and "the job already finished" in r.text
    assert client.delete("/api/jobs/" + "0" * 32).status_code == 404
    assert client.delete("/api/jobs/not-an-id").status_code == 404


def test_second_fix_on_a_busy_map_returns_the_same_job(client, jobs_api, gate, a_map_id) -> None:
    jobs_api.jobs.submit("block")
    a = client.post(f"/api/maps/{a_map_id}/fix").json()["job"]
    assert client.post(f"/api/maps/{a_map_id}/fix").json()["job"] == a
