"""Relight: a copy of a map in another vanilla environment with a regenerated lightshow."""

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.api.jobs_api import core_handlers
from saber_tooth.jobs import Jobs
from saber_tooth.mapio import load_map
from saber_tooth.service import map_id_for
from saber_tooth.service import relight as relight_mod
from saber_tooth.service.relight import UnknownEnvironment, environment_names
from tests.test_api import MID, _wait
from tests.test_service import NAME, _hashes, _make


def _other(svc) -> str:
    names = environment_names(svc._templates())
    current = load_map(svc.levels / NAME).info.environment
    return next(n for n in names if n != current)


def test_relight_writes_a_copy_with_the_new_environment_and_lights(tmp_path):
    svc = _make(tmp_path)
    original = svc.levels / NAME
    before = _hashes(original)
    env = _other(svc)
    report = svc.relight_map(map_id_for(NAME), env)
    assert report["folder"] == f"{NAME} [saber-tooth]" and report["environment"] == env
    assert report["fixed_id"] == map_id_for(report["folder"])
    assert _hashes(original) == before
    copy = load_map(svc.levels / report["folder"])
    assert copy.info.environment == env
    assert any(d.events for d in copy.difficulties.values())
    assert copy.info.song_name.endswith(" [saber-tooth]")


def test_relight_refuses_an_environment_without_templates(tmp_path):
    svc = _make(tmp_path)
    with pytest.raises(UnknownEnvironment):
        svc.relight_map(map_id_for(NAME), "NoSuchEnvironment")
    assert [p.name for p in svc.levels.iterdir()] == [NAME]


def test_cancelled_relight_writes_nothing(tmp_path, monkeypatch):
    svc = _make(tmp_path)
    mid = map_id_for(NAME)
    jobs = Jobs(svc.store)
    for k, h in core_handlers(svc).items():
        jobs.register(k, h)
    job_id = svc.store.create_job("relight", mid, {"map_id": mid, "environment": _other(svc)})
    real = relight_mod.build_lightshow

    def build_then_cancel(*args, **kw):
        out = real(*args, **kw)
        jobs.request_cancel(job_id)
        return out

    monkeypatch.setattr(relight_mod, "build_lightshow", build_then_cancel)
    jobs.start()
    row = jobs.wait(job_id)
    jobs.shutdown()
    assert row["status"] == "cancelled" and row["result"] is None
    assert [p.name for p in svc.levels.iterdir()] == [NAME]


def test_relight_route_runs_a_job_and_lists_environments(tmp_path):
    svc = _make(tmp_path)
    env = _other(svc)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        listed = http.get("/api/lightshow/environments").json()["environments"]
        assert env in listed and listed == sorted(listed)
        jid = http.post(f"/api/maps/{MID}/relight", json={"environment": env}).json()["job"]
        job = _wait(http, jid)
        assert job["status"] == "done" and job["kind"] == "relight"
        assert job["result"]["environment"] == env


def test_relight_route_validates_input(tmp_path):
    svc = _make(tmp_path)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        bad = http.post(f"/api/maps/{MID}/relight", json={"environment": "Nope"})
        assert bad.status_code == 422 and "error" in bad.json()
        assert http.post(f"/api/maps/{MID}/relight", json=[1]).status_code == 422
        assert http.post(f"/api/maps/{MID}/relight", content=b"x").status_code == 400
        gone = http.post(f"/api/maps/{'0' * 12}/relight", json={"environment": _other(svc)})
        assert gone.status_code == 404


def _notes(folder):
    return {n: d.notes for n, d in load_map(folder).difficulties.items()}


def _fixed_pair(tmp_path):
    from tests.test_fix_map import CLASH

    svc = _make(tmp_path, extra=CLASH)
    fixed = svc.fix_map(map_id_for(NAME))["folder"]
    return svc, svc.levels / NAME, svc.levels / fixed


def test_relighting_an_original_with_a_copy_relights_the_copy(tmp_path):
    svc, original, copy = _fixed_pair(tmp_path)
    before, notes, env = _hashes(original), _notes(copy), _other(svc)
    report = svc.relight_map(map_id_for(NAME), env)
    assert report["folder"] == copy.name and report["created"] is False
    assert sorted(p.name for p in svc.levels.iterdir()) == sorted([original.name, copy.name])
    assert _hashes(original) == before and _notes(copy) == notes  # fixes kept
    assert load_map(copy).info.environment == env
    assert load_map(copy).info.song_name.count("[saber-tooth]") == 1


def test_relighting_a_copy_rewrites_that_copy(tmp_path):
    svc, original, copy = _fixed_pair(tmp_path)
    before, notes, env = _hashes(original), _notes(copy), _other(svc)
    report = svc.relight_map(map_id_for(copy.name), env)
    assert report["folder"] == copy.name and report["created"] is False
    assert sorted(p.name for p in svc.levels.iterdir()) == sorted([original.name, copy.name])
    assert _hashes(original) == before and _notes(copy) == notes
    assert load_map(copy).info.environment == env


def test_relighting_an_original_without_a_copy_creates_one(tmp_path):
    svc = _make(tmp_path)
    assert svc.relight_map(map_id_for(NAME), _other(svc))["created"] is True
