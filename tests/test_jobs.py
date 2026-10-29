import threading
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


def test_jobs_run_in_submit_order(env) -> None:
    store, jobs = env
    seen: list[int] = []
    jobs.register("note", lambda args, progress: seen.append(args["n"]) or {"n": args["n"]})
    ids = [jobs.submit("note", {"n": n}) for n in range(5)]
    for job_id in ids:
        assert jobs.wait(job_id)["status"] == "done"
    assert seen == [0, 1, 2, 3, 4]
    assert store.job(ids[2])["result"] == {"n": 2}


def test_a_failing_handler_does_not_stop_later_jobs(env) -> None:
    _, jobs = env

    def boom(args, progress):
        raise RuntimeError("boom")

    jobs.register("boom", boom)
    jobs.register("ok", lambda args, progress: {"ok": True})
    bad = jobs.submit("boom")
    good = jobs.submit("ok")
    assert jobs.wait(bad)["error"] == "boom"
    assert jobs.wait(good)["status"] == "done"


def test_unknown_kind_and_bad_args_fail_that_job_only(env) -> None:
    store, jobs = env
    jobs.register("ok", lambda args, progress: None)
    unknown = store.create_job("nope", None, {})
    broken = store.create_job("ok", None, {})
    store._exec("UPDATE jobs SET args_json='[1' WHERE id=?", (broken,))
    after = jobs.submit("ok")
    assert jobs.wait(unknown)["error"] == "unknown job kind: nope"
    assert jobs.wait(broken)["status"] == "failed"
    assert jobs.wait(after)["status"] == "done"


def test_cancelled_job_is_skipped(env) -> None:
    store, jobs = env
    gate = threading.Event()
    ran: list[str] = []
    jobs.register("block", lambda args, progress: gate.wait(5))
    jobs.register("mark", lambda args, progress: ran.append(args["tag"]))
    first = jobs.submit("block")
    skipped = jobs.submit("mark", {"tag": "skipped"})
    kept = jobs.submit("mark", {"tag": "kept"})
    assert store.cancel_job(skipped) == "cancelled"
    gate.set()
    jobs.wait(first)
    jobs.wait(kept)
    assert ran == ["kept"]


def test_progress_is_recorded(env) -> None:
    _, jobs = env

    def work(args, progress):
        progress("round 1 of 6")
        return None

    jobs.register("work", work)
    job_id = jobs.submit("work")
    assert jobs.wait(job_id)["progress"] == "round 1 of 6"


def test_queued_rows_from_a_previous_process_run_on_start(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    waiting = store.create_job("note", None, {"n": 7})
    jobs = Jobs(store)
    jobs.register("note", lambda args, progress: {"n": args["n"]})
    jobs.start()
    try:
        assert jobs.wait(waiting)["result"] == {"n": 7}
    finally:
        jobs.shutdown()


def test_dedupe_passes_through(env) -> None:
    _, jobs = env
    gate = threading.Event()
    jobs.register("block", lambda args, progress: gate.wait(5))
    a = jobs.submit("block", {}, map_id="m1", dedupe=True)
    assert jobs.submit("block", {}, map_id="m1", dedupe=True) == a
    gate.set()
    jobs.wait(a)
