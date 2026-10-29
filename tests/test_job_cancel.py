import time

from saber_tooth.jobs import Jobs
from saber_tooth.store import Store
from tests.test_api_jobs import api, claimed, client, jobs_api  # noqa: F401


def test_cancelling_a_running_job_ends_it_cancelled_and_the_queue_moves_on(client, jobs_api):  # noqa: F811
    api = jobs_api  # noqa: F811

    def spin(args, progress):
        while True:
            progress("working")
            time.sleep(0.005)

    api.jobs.register("spin", spin)
    api.jobs.register("ok", lambda args, progress: {"ok": True})
    running = api.jobs.submit("spin")
    nxt = api.jobs.submit("ok")
    claimed(api, running)
    assert client.get(f"/api/jobs/{running}").json()["cancel_requested"] is False
    r = client.delete(f"/api/jobs/{running}")
    assert r.status_code == 200 and r.json()["status"] == "running"
    assert r.json()["cancel_requested"] is True
    assert client.delete(f"/api/jobs/{running}").status_code == 200
    assert api.jobs.wait(running)["status"] == "cancelled"
    done = api.store.job(running)
    assert done["error"] is None and done["result"] is None
    assert api.jobs.wait(nxt)["status"] == "done"
    final = client.get(f"/api/jobs/{running}").json()
    assert final["cancel_requested"] is False and final["status"] == "cancelled"
    listed = client.get("/api/jobs").json()
    assert all("cancel_requested" in j for k in listed for j in listed[k])


def test_check_raises_only_after_a_request(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store)
    seen: list[str] = []
    ids: list[str] = []

    def handler(args, progress):
        progress.check()
        seen.append("before")
        jobs.request_cancel(ids[0])
        progress.check()
        seen.append("after")

    jobs.register("h", handler)
    ids.append(store.create_job("h", None, {}))
    jobs.start()
    assert jobs.wait(ids[0])["status"] == "cancelled"
    jobs.shutdown()
    assert seen == ["before"]


def test_fix_beatmap_checks_once_per_finding_attempt():
    import pytest

    from saber_tooth.jobs import JobCancelled
    from saber_tooth.service.fix import fix_beatmap
    from tests.test_fixer_chain import _chain

    calls: list[int] = []

    def check():
        calls.append(1)
        if len(calls) == 2:
            raise JobCancelled

    with pytest.raises(JobCancelled):
        fix_beatmap(_chain(4), None, None, 1, check=check)
    assert len(calls) == 2


def test_request_for_an_idle_or_unknown_job_is_ignored(tmp_path):
    jobs = Jobs(Store(tmp_path / "db.sqlite"))
    jobs.request_cancel("nope")
    assert jobs.cancel_requested("nope") is False


def test_cancel_between_claim_and_start_is_not_lost(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store)
    called: list[int] = []
    jobs.register("h", lambda args, progress: called.append(1))
    job_id = store.create_job("h", None, {})
    jobs.request_cancel(job_id)  # still queued: ignored
    assert jobs.cancel_requested(job_id) is False
    claimed_row = store.claim_next_job()  # running, worker not yet in _run
    jobs.request_cancel(job_id)
    assert jobs.cancel_requested(job_id) is True
    jobs._run(claimed_row)
    row = store.job(job_id)
    assert row["status"] == "cancelled" and row["error"] is None and called == []
    assert jobs.cancel_requested(job_id) is False


def test_fix_map_checks_before_saving():
    from types import SimpleNamespace

    import pytest

    from saber_tooth.jobs import JobCancelled
    from saber_tooth.service import fix as fixmod

    original = object()
    svc = SimpleNamespace(
        _folder=lambda m: "f",
        _load=lambda f: original,
        _analyse=lambda *a: None,
        _templates=lambda: None,
    )

    def boom():
        raise JobCancelled

    progress = lambda text: None  # noqa: E731
    progress.check = boom
    run = SimpleNamespace(rounds=1, steps=[1], unfixed=[], fixed=original)
    orig_checks, orig_fb = fixmod.run_checks, fixmod.fix_beatmap
    fixmod.run_checks = lambda *a: []
    fixmod.fix_beatmap = lambda *a, **k: run
    try:
        with pytest.raises(JobCancelled):
            fixmod.fix_map(svc, "a" * 32, progress=progress)
    finally:
        fixmod.run_checks, fixmod.fix_beatmap = orig_checks, orig_fb
