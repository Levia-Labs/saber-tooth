### Task 2: One worker thread drains the queue

**Files:**

- Rewrite: `src/saber_tooth/jobs.py`
- Test: `tests/test_jobs.py` (rewrite), `tests/test_service_more.py` (update its `Jobs` use, around line 83)

**Interfaces:**

- Consumes: `Store.create_job`, `claim_next_job`, `set_job_progress`, `update_job`, `job` from Task 1.
- Produces:
  - `Progress = Callable[[str], None]`, `Handler = Callable[[dict, Progress], Any]`
  - `Jobs(store)`, `.register(kind: str, handler: Handler) -> None`, `.submit(kind: str, args: dict | None = None, map_id: str | None = None, dedupe: bool = False) -> str`, `.start() -> None` (idempotent), `.wait(job_id: str, timeout: float = 10.0) -> dict` (test helper, returns the finished row), `.shutdown() -> None`
  - `Jobs.future` is removed.

- [ ] **Step 1: Write the failing tests**

`tests/test_jobs.py`:

```python
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
    store, jobs = env

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
```

In `tests/test_service_more.py`, replace the closure submit around line 83 with a registered handler: `jobs.register("<kind>", lambda args, progress: <the old call>)`, `job_id = jobs.submit("<kind>", {...})`, and `jobs.wait(job_id)` in place of `jobs.future(job_id).result()`. Keep each test's assertions.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `task st:test -- tests/test_jobs.py tests/test_service_more.py -q`
Expected: FAIL (`Jobs` has no `register`).

- [ ] **Step 3: Implement**

`src/saber_tooth/jobs.py`:

```python
"""One worker thread drains the durable job queue in the store, oldest first.

Each job kind has a registered handler taking (args, progress). Queued rows survive a
restart because the queue is the `jobs` table, not an in-memory executor.
"""

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from saber_tooth.store import Store

log = logging.getLogger(__name__)

Progress = Callable[[str], None]
Handler = Callable[[dict, Progress], Any]
IDLE_WAIT_S = 5.0  # fallback poll when no submit wakes the worker
FINISHED = ("done", "failed", "cancelled")


class Jobs:
    def __init__(self, store: Store) -> None:
        self._store = store
        self._handlers: dict[str, Handler] = {}
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._start_lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def register(self, kind: str, handler: Handler) -> None:
        self._handlers[kind] = handler

    def submit(
        self,
        kind: str,
        args: dict | None = None,
        map_id: str | None = None,
        dedupe: bool = False,
    ) -> str:
        job_id = self._store.create_job(kind, map_id, args, dedupe=dedupe)
        self.start()
        self._wake.set()
        return job_id

    def start(self) -> None:
        """Start the worker once every handler is registered; later calls do nothing."""
        with self._start_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="jobs", daemon=True)
            self._thread.start()

    def wait(self, job_id: str, timeout: float = 10.0) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            row = self._store.job(job_id)
            if row["status"] in FINISHED or time.monotonic() > deadline:
                return row
            time.sleep(0.01)

    def shutdown(self) -> None:
        """Stop after the current job; queued rows stay for the next start."""
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._store.claim_next_job()
            except Exception:
                log.exception("could not claim a job")
                job = None
            if job is None:
                self._wake.wait(IDLE_WAIT_S)
                self._wake.clear()
                continue
            self._run(job)

    def _run(self, job: dict) -> None:
        job_id = job["id"]
        handler = self._handlers.get(job["kind"])
        if handler is None:
            self._mark_failed(job_id, f"unknown job kind: {job['kind']}")
            return
        try:
            args = json.loads(job.get("args_json") or "{}")
            if not isinstance(args, dict):
                raise ValueError("job arguments are not an object")
        except ValueError as exc:
            self._mark_failed(job_id, f"unreadable job arguments: {exc}")
            return
        try:
            result = handler(args, lambda text: self._store.set_job_progress(job_id, text))
            self._store.update_job(job_id, "done", result=result)
        except Exception as exc:
            self._mark_failed(job_id, str(exc), getattr(exc, "result", None))

    def _mark_failed(self, job_id: str, error: str, result: Any = None) -> None:
        try:
            self._store.update_job(job_id, "failed", error=error, result=result)
        except BaseException:
            log.exception("could not mark job %s failed", job_id)
```

Why the worker parses the raw `args_json` instead of using `job["args"]`: `Store.job` maps unreadable JSON to `{}`, which would silently run a handler with no arguments; the worker must fail such a row instead.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `task st:test -- tests/test_jobs.py tests/test_service_more.py -q`
Expected: PASS. Other suites still calling `jobs.submit(kind, fn, ...)` fail until Task 3; do not fix them here.

- [ ] **Step 5: README and commit**

Update the `jobs.py` row in `src/saber_tooth/README.md`: "`jobs.py`: one worker thread drains the `jobs` table oldest first through handlers registered per kind; queued jobs survive a restart."

Main thread commits: `task st:commit -- -m "feat(jobs): one worker thread drains the durable queue through registered handlers" src/saber_tooth/jobs.py src/saber_tooth/README.md tests/test_jobs.py tests/test_service_more.py`

---
