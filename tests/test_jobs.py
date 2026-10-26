from concurrent.futures import Future
from pathlib import Path

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
