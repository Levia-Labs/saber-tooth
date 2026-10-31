"""The job dispatcher drains the durable queue in the store, oldest first, up to a cap.

Each job kind has a registered handler taking (args, progress). Queued rows survive a
restart because the queue is the `jobs` table, not an in-memory executor. One dispatcher
thread claims jobs; each runs on its own thread, so at most `limit()` jobs run at once. Kinds
given to `enable_processes` run in a spawned worker process instead when the cap is above one,
which is what makes CPU-bound handlers use several cores. Two jobs on one map never run
together. The cap is read on every pass, so a changed setting applies to the next job started.
"""

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from saber_tooth.jobs_child import ChildRunner, Factory, share_store
from saber_tooth.jobs_claim import claim_job
from saber_tooth.jobs_errors import JobCancelled, error_text
from saber_tooth.store import Store

log = logging.getLogger(__name__)


class _Progress:
    """Progress callback handed to handlers; every call is a cancellation checkpoint."""

    def __init__(self, jobs: "Jobs", job_id: str) -> None:
        self._jobs, self._id = jobs, job_id

    def check(self) -> None:
        if self._jobs.cancel_requested(self._id):
            raise JobCancelled

    def __call__(self, text: str) -> None:
        self.check()
        self._jobs._store.set_job_progress(self._id, text)


Progress = Callable[[str], None]  # the object handed in also has `.check()`
Handler = Callable[[dict, Progress], Any]
IDLE_WAIT_S = 5.0  # fallback poll when no submit wakes the worker
FINISHED = ("done", "failed", "cancelled")


class Jobs:
    def __init__(self, store: Store, limit: Callable[[], int] | None = None) -> None:
        self._store = store
        self._limit = limit or (lambda: 1)  # most jobs running at once; read on every pass
        self._handlers: dict[str, Handler] = {}
        # Per kind, run in this process with (args, result) once a job of the kind is done.
        self.after_done: dict[str, Callable[[dict, Any], None]] = {}
        self._children: ChildRunner | None = None
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._start_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._cancel_lock = threading.Lock()
        self._cancel_ids: set[str] = set()  # running jobs asked to stop
        self._active_lock = threading.Lock()
        self._active: dict[str, str | None] = {}  # running job id -> its map id
        self._runners: set[threading.Thread] = set()

    def register(self, kind: str, handler: Handler) -> None:
        self._handlers[kind] = handler

    def enable_processes(self, factory: Factory, kinds: frozenset[str] | set[str]) -> None:
        """Run these kinds in worker processes; `factory` (picklable) rebuilds their handlers."""
        share_store(self._store)
        self._children = ChildRunner(factory, frozenset(kinds))

    def set_limit(self, limit: Callable[[], int]) -> None:
        """Replace the cap source; it is read before each claim."""
        self._limit = limit

    def running_count(self) -> int:
        with self._active_lock:
            return len(self._active)

    def poke(self) -> None:
        """Wake the dispatcher, e.g. after the cap was raised."""
        self._wake.set()

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
        """Start the dispatcher once every handler is registered; later calls do nothing."""
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
        """Stop claiming and wait for running jobs; queued rows stay for the next start."""
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join()
        with self._active_lock:
            runners = list(self._runners)
        for runner in runners:
            runner.join()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._wake.clear()  # before the claim, so a submit during it is not lost
            job = None
            if self.running_count() < max(1, self._limit()):
                try:
                    with self._active_lock:
                        busy = {m for m in self._active.values() if m}
                    job = claim_job(self._store, busy)
                except Exception:
                    log.exception("could not claim a job")
            if job is None:
                self._wake.wait(IDLE_WAIT_S)
                continue
            self._launch(job)

    def _launch(self, job: dict) -> None:
        runner = threading.Thread(target=self._slot, args=(job,), name=f"job-{job['id'][:8]}")
        runner.daemon = True
        with self._active_lock:
            self._active[job["id"]] = job.get("map_id")
            self._runners.add(runner)
        runner.start()

    def _slot(self, job: dict) -> None:
        try:
            self._run(job)
        finally:
            with self._active_lock:
                self._active.pop(job["id"], None)
                self._runners.discard(threading.current_thread())
            self._wake.set()  # a slot and a map came free

    def _run(self, job: dict) -> None:
        try:
            self._execute(job)
        finally:
            with self._cancel_lock:
                self._cancel_ids.discard(job["id"])

    def _execute(self, job: dict) -> None:
        job_id = job["id"]
        # With a cap of one nothing runs beside the job, so a process buys no parallelism and
        # would lose the warm in-memory caches: the handler runs in this process instead.
        in_child = (
            self._children is not None and job["kind"] in self._children.kinds and self._limit() > 1
        )
        handler = self._handlers.get(job["kind"])
        if handler is None and not in_child:
            self._mark_failed(job_id, f"unknown job kind: {job['kind']}")
            return
        try:
            args = json.loads(job.get("args_json") or "{}")
            if not isinstance(args, dict):
                raise ValueError("job arguments are not an object")
        except ValueError as exc:
            self._mark_failed(job_id, f"unreadable job arguments: {exc}")
            return
        if job.get("map_id") and "map_id" not in args:
            args["map_id"] = job["map_id"]  # a row queued without args still knows its map
        progress = _Progress(self, job_id)
        try:
            progress.check()  # cancelled between claim and start
            if in_child:
                result = self._children.run(
                    job["kind"],
                    args,
                    lambda text: self._store.set_job_progress(job_id, text),
                    lambda: self.cancel_requested(job_id),
                )
            else:
                result = handler(args, progress)
            after = self.after_done.get(job["kind"])
            if after is not None:
                try:
                    after(args, result)
                except Exception:
                    log.exception("after-done hook of job %s failed", job_id)
            self._store.update_job(job_id, "done", result=result)
        except JobCancelled:
            self._store.update_job(job_id, "cancelled")
        except Exception as exc:
            log.exception("job %s (%s) failed", job_id, job["kind"])
            self._mark_failed(job_id, error_text(exc), getattr(exc, "result", None))

    def request_cancel(self, job_id: str) -> None:
        """Ask a running job to stop at its next checkpoint; other jobs are ignored."""
        try:
            running = self._store.job(job_id)["status"] == "running"
        except KeyError:
            return
        if running:
            with self._cancel_lock:
                self._cancel_ids.add(job_id)

    def cancel_requested(self, job_id: str) -> bool:
        with self._cancel_lock:
            return job_id in self._cancel_ids

    def _mark_failed(self, job_id: str, error: str, result: Any = None) -> None:
        try:
            self._store.update_job(job_id, "failed", error=error, result=result)
        except BaseException:
            log.exception("could not mark job %s failed", job_id)
