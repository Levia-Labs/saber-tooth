import pytest

from tests.test_api_jobs import a_map_id, api, client, jobs_api  # noqa: F401

RETRY = "/api/jobs/{}/retry"


def _failed(jobs, attempts: list):
    def flaky(args, progress):
        attempts.append(args)
        if len(attempts) == 1:
            raise RuntimeError("first try fails")
        return {"ok": True, "args": args}

    jobs.register("flaky", flaky)
    job_id = jobs.submit("flaky", {"n": 1}, map_id="abc123def456")
    assert jobs.wait(job_id)["status"] == "failed"
    return job_id


def test_retrying_a_failed_job_queues_a_new_one_with_the_same_kind_and_args(client, jobs_api):  # noqa: F811
    attempts: list = []
    failed = _failed(jobs_api.jobs, attempts)
    r = client.post(RETRY.format(failed))
    assert r.status_code == 200
    view = r.json()
    assert view["id"] != failed and view["kind"] == "flaky" and view["status"] == "queued"
    assert view["map_id"] == "abc123def456"
    done = jobs_api.jobs.wait(view["id"])
    with pytest.raises(KeyError):  # the retry's result supersedes the failed row for that map
        jobs_api.store.job(failed)
    assert done["status"] == "done" and done["result"]["args"] == {"n": 1, "map_id": "abc123def456"}
    assert [a["n"] for a in attempts] == [1, 1]  # the handler also sees the row's map_id


def test_only_a_failed_job_can_be_retried(client, jobs_api):  # noqa: F811
    jobs_api.jobs.register("ok", lambda args, progress: {"ok": True})
    done = jobs_api.jobs.submit("ok")
    assert jobs_api.jobs.wait(done)["status"] == "done"
    r = client.post(RETRY.format(done))
    assert r.status_code == 409
    assert r.json() == {"error": "only a failed or cancelled job can be restarted"}
    assert len(client.get("/api/jobs").json()["recent"]) == 1


def test_retrying_a_queued_job_is_refused(client, jobs_api):  # noqa: F811
    queued = jobs_api.store.create_job("ok", None, {})  # the worker is not started
    assert client.post(RETRY.format(queued)).status_code == 409


def test_a_cancelled_job_can_be_restarted(client, jobs_api):  # noqa: F811
    jobs_api.jobs.register("ok", lambda args, progress: {"ok": True, "args": args})
    cancelled = jobs_api.store.create_job("ok", "abc123def456", {"n": 2})
    jobs_api.store.cancel_job(cancelled)
    r = client.post(RETRY.format(cancelled))
    assert r.status_code == 200
    new = r.json()
    assert new["id"] != cancelled and new["kind"] == "ok" and new["status"] == "queued"
    assert new["map_id"] == "abc123def456"


def test_retrying_an_unknown_job_is_404(client):  # noqa: F811
    assert client.post(RETRY.format("0" * 32)).status_code == 404
    assert client.post(RETRY.format("nope")).status_code == 404


def _failed_upload(jobs_api, upload: str):  # noqa: F811
    jobs_api.jobs.register("generate", lambda args, progress: (_ for _ in ()).throw(OSError("x")))
    job_id = jobs_api.jobs.submit("generate", {"upload": upload})
    assert jobs_api.jobs.wait(job_id)["status"] == "failed"
    return job_id


def test_retrying_a_generate_whose_upload_is_gone_is_refused(client, jobs_api):  # noqa: F811
    gone = jobs_api.service.data / "uploads" / "abc" / "song.mp3"
    failed = _failed_upload(jobs_api, str(gone))
    r = client.post(RETRY.format(failed))
    assert r.status_code == 409
    assert r.json() == {"error": "the uploaded audio is gone; upload it again"}
    assert len(client.get("/api/jobs").json()["recent"]) == 1


def test_retrying_a_generate_with_its_upload_still_there_is_queued(client, jobs_api):  # noqa: F811
    song = jobs_api.service.data / "uploads" / "abc" / "song.mp3"
    song.parent.mkdir(parents=True)
    song.write_bytes(b"x")
    failed = _failed_upload(jobs_api, str(song))
    assert client.post(RETRY.format(failed)).status_code == 200


@pytest.mark.parametrize("kind", ["scan", "fix", "apply", "crop", "relight"])
def test_retrying_a_map_job_whose_map_is_gone_is_409(client, jobs_api, kind):  # noqa: F811
    jobs_api.jobs.register(kind, lambda args, progress: {"ok": True})
    orphan = jobs_api.store.create_job(kind, None, {})
    jobs_api.store.cancel_job(orphan)
    r = client.post(RETRY.format(orphan))
    assert r.status_code == 409
    assert r.json() == {"error": "this job's map is gone"}


def test_library_item_carries_the_job_position_and_progress(client, jobs_api, a_map_id):  # noqa: F811
    first = jobs_api.store.create_job("fix", a_map_id, {})
    items = client.get("/api/maps").json()["items"]
    job = next(i for i in items if i["id"] == a_map_id)["job"]
    assert job == {"id": first, "kind": "fix", "status": "queued", "position": 1, "progress": None}
    jobs_api.store.claim_next_job()
    jobs_api.store.set_job_progress(first, "round 2 of 5")
    items = client.get("/api/maps").json()["items"]
    job = next(i for i in items if i["id"] == a_map_id)["job"]
    assert job["status"] == "running" and job["position"] is None
    assert job["progress"] == "round 2 of 5"
