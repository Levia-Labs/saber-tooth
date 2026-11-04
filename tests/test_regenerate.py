"""Regenerate job, bulk fix and regenerate routes, the findings summary and its CLI."""

import httpx
import pytest
from fastapi.testclient import TestClient

from saber_tooth.analyser_client import AnalyserClient
from saber_tooth.api import create_app
from saber_tooth.cli_library import findings_lines, queue_bulk
from saber_tooth.findings_summary import findings_summary
from saber_tooth.mapio import load_map, write_map
from saber_tooth.service import Service, map_id_for
from saber_tooth.service.regenerate import NotGenerated, regenerate_map
from saber_tooth.service.relight import environment_names
from saber_tooth.store import Store
from tests.test_service import NAME, _make
from tests.test_service_generate import _copy, _project

URL = "https://www.youtube.com/watch?v=VKUGl7wR7Dg"
SOURCE = "yt:VKUGl7wR7Dg"


@pytest.fixture
def gen(tmp_path):
    _project(tmp_path / "up")

    def handler(request):
        headers = {"Content-Disposition": 'attachment; filename="song1_tracks.zip"'}
        return httpx.Response(200, content=b"zip", headers=headers)

    client = AnalyserClient("http://analyser", tmp_path / "up", httpx.MockTransport(handler))
    levels, data = tmp_path / "levels", tmp_path / "data"
    levels.mkdir()
    data.mkdir()
    s = Service(levels, data, Store(data / "s.db"), client, _copy)
    s.probe_tags = lambda path: {}
    return s


def _generated(svc):
    result = svc.run_generate(URL)
    svc.store.set_source(result["map_id"], SOURCE)
    return result


def _finding(rule, severity="warn"):
    return {
        "rule": rule,
        "severity": severity,
        "difficulty": "Easy",
        "beat_start": 1.0,
        "beat_end": 2.0,
        "message": "m",
    }


def test_regenerate_keeps_names_cover_id_and_environment_and_backs_up(gen):
    svc = gen
    result = _generated(svc)
    folder = svc.levels / result["folder"]
    old = load_map(folder)
    env = next(e for e in environment_names(svc._templates()) if e != old.info.environment)
    old.info.environment = env
    write_map(old, folder, None)
    (folder / "cover.png").write_bytes(b"my-cover")
    out = regenerate_map(svc, result["map_id"])
    new = load_map(folder)
    assert out["map_id"] == result["map_id"] and out["folder"] == result["folder"]
    assert (new.info.song_name, new.info.author) == (old.info.song_name, old.info.author)
    assert new.info.environment == env
    assert (folder / "cover.png").read_bytes() == b"my-cover"
    assert (folder / "song.egg").is_file()
    assert (svc.data / "backups" / folder.name / "cover.png").is_file()
    assert map_id_for(folder.name) == result["map_id"]
    assert svc.store.find_source(SOURCE)["id"] == result["map_id"]
    assert not list((svc.data / "staging").iterdir())
    assert not [p for p in svc.levels.iterdir() if p.name.startswith(".")]
    assert len([p for p in svc.levels.iterdir()]) == 1


def test_regenerate_refuses_a_map_without_source(tmp_path):
    svc = _make(tmp_path)
    with pytest.raises(NotGenerated):
        regenerate_map(svc, map_id_for(NAME))


def test_regenerate_falls_back_to_the_stored_link_without_audio(gen):
    svc = gen
    result = _generated(svc)
    (svc.levels / result["folder"] / "song.egg").unlink()
    assert regenerate_map(svc, result["map_id"])["folder"] == result["folder"]


def test_regenerate_route_refuses_human_maps_and_queues_generated_ones(tmp_path):
    svc = _make(tmp_path)
    mid = map_id_for(NAME)
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        refused = c.post(f"/api/maps/{mid}/regenerate")
        assert refused.status_code == 409
        svc.store.set_source(mid, SOURCE)
        ok = c.post(f"/api/maps/{mid}/regenerate")
        assert ok.status_code == 200 and ok.json()["job"]


def test_bulk_routes_queue_one_job_per_map_and_dedupe(tmp_path):
    svc = _make(tmp_path)
    mid = map_id_for(NAME)
    svc.store.set_source(mid, SOURCE)
    svc.store.replace_open_proposals(mid, [], {"findings": [_finding("r1")], "analysis": None})
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        api = c.app.state.api
        api.jobs._stop.set()  # keep the queue from draining while counting
        regen = c.post("/api/maps/regenerate-all").json()
        fixes = c.post("/api/maps/fix-all").json()
        again = c.post("/api/maps/fix-all").json()
    assert regen["count"] == 1 and len(regen["jobs"]) == 1
    assert fixes["count"] == 1 and again["jobs"] == fixes["jobs"]


def test_summary_counts_per_rule_and_severity_and_maps(tmp_path):
    svc = _make(tmp_path)
    mid = map_id_for(NAME)
    findings = [_finding("a"), _finding("a"), _finding("b", "error")]
    svc.store.replace_open_proposals(mid, [], {"findings": findings, "analysis": None})
    out = findings_summary(svc.store)
    assert {(r["rule"], r["severity"]): r["findings"] for r in out["rules"]} == {
        ("a", "warn"): 2,
        ("b", "error"): 1,
    }
    assert out["severities"] == {"warn": 2, "error": 1} and out["findings"] == 3
    assert out["maps"]["with_findings"] == 1 and out["maps"]["total"] >= 1
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        assert c.get("/api/findings/summary").json() == out


def test_cli_helpers_read_the_api():
    def handler(request):
        if request.url.path == "/api/findings/summary":
            return httpx.Response(
                200,
                json={
                    "rules": [{"rule": "x", "severity": "warn", "findings": 4, "maps": 2}],
                    "findings": 4,
                    "maps": {"total": 9, "scanned": 8, "with_findings": 2, "generated": 3},
                },
            )
        return httpx.Response(200, json={"count": 3, "jobs": ["a", "b", "c"]})

    t = httpx.MockTransport(handler)
    assert queue_bulk("/api/maps/fix-all", "http://x", t) == "queued 3 jobs"
    lines = findings_lines("http://x", t)
    assert lines[0].startswith("9 maps") and "x" in lines[1]


def _plain_other_env(svc, result):
    """The map's folder with no colour scheme and an environment the auto-style would not pick."""
    folder = svc.levels / result["folder"]
    old = load_map(folder)
    auto = old.info.environment
    env = next(e for e in environment_names(svc._templates()) if e != auto)
    old.info.environment, old.info.color_scheme = env, None
    write_map(old, folder, None)
    return folder, auto, env


def test_regenerate_restyles_a_map_with_no_scheme_and_no_relight(gen):
    result = _generated(gen)
    folder, auto, env = _plain_other_env(gen, result)
    regenerate_map(gen, result["map_id"])
    assert load_map(folder).info.environment == auto != env


def test_regenerate_keeps_the_environment_a_relight_job_set(gen):
    result = _generated(gen)
    folder, _, env = _plain_other_env(gen, result)
    job = gen.store.create_job("relight", result["map_id"], {"environment": env})
    gen.store._exec("UPDATE jobs SET status='done' WHERE id=?", (job,))
    regenerate_map(gen, result["map_id"])
    assert load_map(folder).info.environment == env
