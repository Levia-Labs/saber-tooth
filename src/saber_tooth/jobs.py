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
