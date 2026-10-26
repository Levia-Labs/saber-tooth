from concurrent.futures import Future
from pathlib import Path
from typing import ClassVar

import pytest

from saber_tooth.jobs import Jobs
from saber_tooth.store import Store


@pytest.fixture
def env(tmp_path: Path):
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store)
    yield store, jobs
    jobs.shutdown()


def _wait(jobs: Jobs, job_id: str) -> None:
    fut: Future = jobs.future(job_id)
    fut.result(timeout=5)


def test_job_done_with_result(env) -> None:
    store, jobs = env
    jid = jobs.submit("scan", lambda a, b: {"sum": a + b}, 1, 2)
    _wait(jobs, jid)
    job = store.job(jid)
    assert job["status"] == "done"
    assert job["result"] == {"sum": 3}


def test_job_failure_records_message(env) -> None:
    store, jobs = env

    def boom() -> None:
        raise RuntimeError("kaboom")

    jid = jobs.submit("scan", boom)
    _wait(jobs, jid)
    job = store.job(jid)
    assert job["status"] == "failed"
    assert job["error"] == "kaboom"


def test_unserialisable_result_fails(env) -> None:
    store, jobs = env
    jid = jobs.submit("scan", lambda: {1, 2})
    _wait(jobs, jid)
    assert store.job(jid)["status"] == "failed"


def test_failed_job_keeps_result_payload(env) -> None:
    store, jobs = env

    class Boom(Exception):
        result: ClassVar = {"conflict": [1, 2]}

    def fail():
        raise Boom("nope")

    jid = jobs.submit("apply", fail)
    _wait(jobs, jid)
    job = store.job(jid)
    assert job["status"] == "failed" and job["error"] == "nope"
    assert job["result"] == {"conflict": [1, 2]}
