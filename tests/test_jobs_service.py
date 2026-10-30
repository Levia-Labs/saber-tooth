"""A scan job in a real worker process: its own service, the shared store."""

import shutil
from functools import partial
from pathlib import Path

import httpx

from saber_tooth.analyser_client import AnalyserClient
from saber_tooth.jobs import Jobs
from saber_tooth.jobs_service import PROCESS_KINDS, ChildSpec, build_child_handlers
from saber_tooth.service import Service, map_id_for
from saber_tooth.store import Store

FIXTURE = Path(__file__).parent / "fixtures" / "maps" / "v3_boxes"


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("analyser is not part of this test")


def test_the_child_scans_a_map_the_parent_indexed(tmp_path):
    levels, data = tmp_path / "levels", tmp_path / "data"
    shutil.copytree(FIXTURE, levels / FIXTURE.name)
    data.mkdir()
    store = Store(data / "saber-tooth.db")
    client = AnalyserClient("http://analyser.invalid", data / "up", httpx.MockTransport(_down))
    parent = Service(levels, data, store, client, shutil.copyfile)
    parent.refresh_library()
    map_id = map_id_for(FIXTURE.name)

    spec = ChildSpec(
        str(levels), str(data), str(data / "saber-tooth.db"), "http://analyser.invalid", str(data)
    )
    jobs = Jobs(store, limit=lambda: 2)
    jobs.enable_processes(partial(build_child_handlers, spec), PROCESS_KINDS)
    for kind in PROCESS_KINDS:
        jobs.register(kind, lambda a, p: (_ for _ in ()).throw(AssertionError("ran inline")))
    try:
        job = jobs.submit("scan", {"map_id": map_id}, map_id=map_id)
        row = jobs.wait(job, 120)
    finally:
        jobs.shutdown()
    assert row["status"] == "done", row["error"]
    assert len(store.proposals(map_id)) > 0  # written by the child, read through the parent


def test_the_production_service_carries_a_child_spec(tmp_path, monkeypatch):
    from saber_tooth.api import build_service

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LEVELS_DIR", str(tmp_path / "levels"))
    monkeypatch.setenv("ANALYSER_URL", "http://analyser:8000")
    (tmp_path / "levels").mkdir()
    spec = build_service().child_spec
    assert spec.levels == str(tmp_path / "levels")
    assert spec.db == str(tmp_path / "data" / "saber-tooth.db")
    assert spec.analyser_url == "http://analyser:8000"
