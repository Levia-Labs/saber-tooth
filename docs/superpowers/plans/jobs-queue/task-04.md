### Task 4: `GET /api/jobs`, job detail fields and cancel

**Files:**

- Modify: `src/saber_tooth/api/jobs_api.py`
- Modify: `src/saber_tooth/api/core.py` (`job`, lines 261-268)
- Modify: `src/saber_tooth/api/__init__.py` (routes near line 174)
- Test: `tests/test_api_jobs.py` (new)

**Interfaces:**

- Consumes: `Store.job`, `job_lists`, `queue_position`, `cancel_job` (Task 1).
- Produces:
  - JSON job view: `id`, `kind`, `status`, `map_id`, `title`, `map_exists`, `created_at`, `started_at`, `updated_at`, `progress`, `progress_at`, `error`, `position` (int when queued, else null); the detail view adds `result`.
  - `GET /api/jobs` returns `{"running": [view], "queued": [view], "recent": [view]}`.
  - `DELETE /api/jobs/{id}`: 200 with the cancelled view; 409 "a running job cannot be stopped"; 409 "the job already finished"; 404 "unknown job: <id>".
  - `Api.jobs_list() -> dict`, `Api.job(raw) -> dict`, `Api.cancel_job(raw) -> dict`.

- [ ] **Step 1: Write the failing tests**

`tests/test_api_jobs.py` builds the app the same way the existing API tests do (copy the fixture pattern from `tests/test_api.py`: `create_app(service, ...)` plus `TestClient`), then blocks the worker so queue states are stable:

```python
import threading

import pytest

# `client` and `api` fixtures: copy the app construction from tests/test_api.py and expose
# both the TestClient and the Api instance (create_app's `api` is reachable through the
# service fixture there; follow whatever that file does).


@pytest.fixture
def gate(api):
    gate = threading.Event()
    api.jobs.register("block", lambda args, progress: gate.wait(5))
    yield gate
    gate.set()


def test_list_shape_positions_and_titles(client, api, gate) -> None:
    running = api.jobs.submit("block")
    q1 = api.jobs.submit("block")
    q2 = api.jobs.submit("generate", {"url": "https://youtu.be/x"})
    api.jobs.wait(running, timeout=0.2)  # let the worker claim the first
    body = client.get("/api/jobs").json()
    assert [j["id"] for j in body["running"]] == [running]
    assert [(j["id"], j["position"]) for j in body["queued"]] == [(q1, 1), (q2, 2)]
    assert body["queued"][1]["title"] == "Generate from YouTube"
    assert body["running"][0]["position"] is None
    assert set(body) == {"running", "queued", "recent"}
    assert "args" not in body["queued"][1] and "result" not in body["queued"][1]


def test_title_is_the_map_title_or_a_kind_label(client, api, gate, a_map_id) -> None:
    blocker = api.jobs.submit("block")
    job = api.jobs.submit("scan", {"map_id": a_map_id}, map_id=a_map_id)
    learn = api.jobs.submit("learn")
    api.jobs.wait(blocker, timeout=0.2)
    queued = {j["id"]: j for j in client.get("/api/jobs").json()["queued"]}
    assert queued[job]["title"] == api.store.get_map(a_map_id)["title"]
    assert queued[job]["map_exists"] is True
    assert queued[learn]["title"] == "Learn lightshows"


def test_detail_has_the_new_fields(client, api, gate) -> None:
    blocker = api.jobs.submit("block")
    waiting = api.jobs.submit("block")
    api.jobs.wait(blocker, timeout=0.2)
    body = client.get(f"/api/jobs/{waiting}").json()
    assert body["status"] == "queued" and body["position"] == 1
    for key in ("result", "started_at", "progress", "progress_at", "title", "map_id"):
        assert key in body


def test_cancel_status_codes(client, api, gate) -> None:
    running = api.jobs.submit("block")
    waiting = api.jobs.submit("block")
    api.jobs.wait(running, timeout=0.2)
    assert client.delete(f"/api/jobs/{waiting}").json()["status"] == "cancelled"
    r = client.delete(f"/api/jobs/{running}")
    assert r.status_code == 409 and "a running job cannot be stopped" in r.text
    gate.set()
    api.jobs.wait(running)
    r = client.delete(f"/api/jobs/{running}")
    assert r.status_code == 409 and "the job already finished" in r.text
    assert client.delete("/api/jobs/" + "0" * 32).status_code == 404
    assert client.delete("/api/jobs/not-an-id").status_code == 404


def test_second_fix_on_a_busy_map_returns_the_same_job(client, api, gate, a_map_id) -> None:
    api.jobs.submit("block")
    a = client.post(f"/api/maps/{a_map_id}/fix").json()["job"]
    assert client.post(f"/api/maps/{a_map_id}/fix").json()["job"] == a
```

`a_map_id`: a fixture returning the id of a map in the library the existing API tests index (copy from `tests/test_api.py`). Check the real Fix route path in `api/__init__.py` and use it in the last test. Error bodies use the app's existing error shape; assert on `r.text` as above.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `task st:test -- tests/test_api_jobs.py -q`
Expected: FAIL (404 or 405 on `/api/jobs`).

- [ ] **Step 3: Implement**

Append to `src/saber_tooth/api/jobs_api.py`:

```python
KIND_LABELS = {
    "scan": "Scan",
    "fix": "Fix",
    "apply": "Apply",
    "crop": "Crop",
    "learn": "Learn lightshows",
    "bs-download": "Download maps",
}
VIEW_FIELDS = (
    "id",
    "kind",
    "status",
    "map_id",
    "created_at",
    "started_at",
    "updated_at",
    "progress",
    "progress_at",
    "error",
)


def _title(row: dict) -> str:
    if row.get("map_title"):
        return row["map_title"]
    if row["kind"] == "generate":
        return "Generate from YouTube" if "url" in row["args"] else "Generate from file"
    return KIND_LABELS.get(row["kind"], row["kind"])


def view(row: dict, position: int | None = None) -> dict:
    out = {k: row.get(k) for k in VIEW_FIELDS}
    out["title"] = _title(row)
    out["map_exists"] = bool(row.get("map_exists"))
    out["position"] = position
    return out


def list_jobs(store) -> dict:
    lists = store.job_lists()
    return {
        "running": [view(r) for r in lists["running"]],
        "queued": [view(r, n) for n, r in enumerate(lists["queued"], start=1)],
        "recent": [view(r) for r in lists["recent"]],
    }


def job_detail(store, job_id: str) -> dict:
    """One job with its result; raises KeyError for an unknown id."""
    row = store.job(job_id)
    found = store.get_map(row["map_id"]) if row.get("map_id") else None
    row["map_title"] = found["title"] if found else None
    row["map_exists"] = found is not None
    out = view(row, store.queue_position(job_id))
    out["result"] = row["result"]
    return out
```

`src/saber_tooth/api/core.py`: replace `job` and add `jobs_list` and `cancel_job` (keep `JOB_ID` validation):

```python
def _job_id(self, raw: str) -> str:
    if not JOB_ID.fullmatch(raw):
        raise ApiError(404, f"unknown job: {raw}")
    return raw


def job(self, raw: str) -> dict:
    try:
        return job_detail(self.store, self._job_id(raw))
    except KeyError:
        raise ApiError(404, f"unknown job: {raw}") from None


def jobs_list(self) -> dict:
    return list_jobs(self.store)


def cancel_job(self, raw: str) -> dict:
    try:
        outcome = self.store.cancel_job(self._job_id(raw))
    except KeyError:
        raise ApiError(404, f"unknown job: {raw}") from None
    if outcome == "running":
        raise ApiError(409, "a running job cannot be stopped")
    if outcome != "cancelled":
        raise ApiError(409, "the job already finished")
    return self.job(raw)
```

Import `job_detail` and `list_jobs` beside `core_handlers`. If `core.py` would pass 300 lines, move `generate_url`/`generate_file` validation helpers it no longer needs, never logic other tasks rely on; report the final count.

`src/saber_tooth/api/__init__.py`, beside the existing `@app.get("/api/jobs/{job_id}")`:

```python
@app.get("/api/jobs")
def jobs():
    return api.jobs_list()


@app.delete("/api/jobs/{job_id}")
def cancel_job(job_id: str):
    return api.cancel_job(job_id)
```

The MCP job tool (`api/mcp_tools.py`) calls `api.job`; its output gains fields, which is fine. Run its tests.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `task st:test -q`
Expected: PASS.

- [ ] **Step 5: README and commit**

`src/saber_tooth/api/README.md`: extend the `jobs_api.py` row with "job views with titles and queue positions, `GET /api/jobs`, cancel of queued jobs". Main thread commits: `task st:commit -- -m "feat(api): GET /api/jobs lists running, queued and recent jobs; DELETE cancels a queued job" <files>`

---
