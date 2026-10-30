"""Jobs in spawned worker processes: isolation, parallelism, progress, failure and cancel."""

import os
import time

import pytest

from saber_tooth.jobs import Jobs
from saber_tooth.store import Store
from tests.jobs_fakes import handlers

KINDS = frozenset({"pid", "spin", "boom", "die", "steps", "hold"})


@pytest.fixture
def make(tmp_path):
    made: list[Jobs] = []

    def build(limit: int = 2):
        store = Store(tmp_path / "db.sqlite")
        jobs = Jobs(store, limit=lambda: limit)
        for kind, handler in handlers().items():
            jobs.register(kind, handler)  # what runs inline when the cap is one
        jobs.enable_processes(handlers, KINDS)
        made.append(jobs)
        return store, jobs

    yield build
    for jobs in made:
        jobs.shutdown()


def test_a_job_runs_in_another_process_and_stores_its_result(make):
    store, jobs = make()
    job = store.create_job("pid", None, {})
    jobs.start()
    row = jobs.wait(job, 60)
    assert row["status"] == "done"
    assert row["result"]["pid"] != os.getpid()


def test_progress_and_the_map_id_reach_the_parent_store(make):
    store, jobs = make()
    job = store.create_job("steps", "m1", {"map_id": "m1"})
    jobs.start()
    row = jobs.wait(job, 60)
    assert row["status"] == "done" and row["result"] == {"steps": 3, "map_id": "m1"}
    assert row["progress"] == "step 2"


def test_a_raising_handler_marks_the_job_failed_with_its_message(make):
    store, jobs = make()
    job = store.create_job("boom", None, {})
    jobs.start()
    row = jobs.wait(job, 60)
    assert row["status"] == "failed" and row["error"] == "kaput"


def test_a_worker_that_dies_marks_the_job_failed(make):
    store, jobs = make()
    job = store.create_job("die", None, {})
    jobs.start()
    row = jobs.wait(job, 60)
    assert row["status"] == "failed" and "exited unexpectedly" in row["error"]
    assert "3" in row["error"]


def test_cancel_stops_a_job_running_in_a_child(make):
    store, jobs = make()
    job = store.create_job("spin", None, {})
    jobs.start()
    deadline = time.monotonic() + 60
    while store.job(job).get("progress") != "spinning" and time.monotonic() < deadline:
        time.sleep(0.05)
    jobs.request_cancel(job)
    row = jobs.wait(job, 30)
    assert row["status"] == "cancelled" and row["error"] is None
    # The flag is cleared just after the row turns cancelled (views mask it by status, so the
    # page never shows a running job as not cancelling); wait for that, do not race it.
    deadline = time.monotonic() + 10
    while jobs.cancel_requested(job) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert jobs.cancel_requested(job) is False
    follow = store.create_job("pid", None, {})
    assert jobs.wait(follow, 60)["status"] == "done"  # the slot came back


def test_a_job_cancelled_before_the_child_starts_never_runs_it(make):
    store, jobs = make()
    job = store.create_job("pid", None, {})
    row = store.claim_next_job()
    jobs.request_cancel(job)
    jobs._run(row)
    assert store.job(job)["status"] == "cancelled"


def test_two_children_overlap_with_a_cap_of_two(make):
    store, jobs = make(2)
    ids = [store.create_job("hold", None, {"seconds": 3}) for _ in range(2)]
    jobs.start()
    rows = [jobs.wait(i, 90) for i in ids]
    assert all(r["status"] == "done" for r in rows)
    starts = sorted(r["result"]["start"] for r in rows)
    assert starts[1] - starts[0] < 3  # the second began before the first could have ended
    assert rows[0]["result"]["pid"] != rows[1]["result"]["pid"]


def test_with_a_cap_of_one_the_handler_runs_in_this_process_and_never_overlaps(make):
    store, jobs = make(1)
    ids = [store.create_job("hold", None, {"seconds": 1}) for _ in range(2)]
    jobs.start()
    rows = [jobs.wait(i, 90) for i in ids]
    assert all(r["status"] == "done" for r in rows)
    assert {r["result"]["pid"] for r in rows} == {os.getpid()}
    starts = sorted(r["result"]["start"] for r in rows)
    assert starts[1] - starts[0] >= 1  # the second began after the first finished sleeping


def test_same_map_children_run_one_at_a_time(make):
    store, jobs = make(2)
    ids = [store.create_job("hold", "m1", {"map_id": "m1", "seconds": 1}) for _ in range(2)]
    jobs.start()
    rows = [jobs.wait(i, 90) for i in ids]
    starts = sorted(r["result"]["start"] for r in rows)
    assert starts[1] - starts[0] >= 1
