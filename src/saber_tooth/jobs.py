"""In-process job worker backed by the store."""

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from saber_tooth.store import Store

log = logging.getLogger(__name__)


class Jobs:
    def __init__(self, store: Store, max_workers: int = 1) -> None:
        self._store = store
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: dict[str, Future] = {}

    def submit(self, kind: str, fn: Callable[..., Any], *args: Any) -> str:
        job_id = self._store.create_job(kind)
        self._futures[job_id] = self._pool.submit(self._run, job_id, fn, args)
        return job_id

    def future(self, job_id: str) -> Future:
        return self._futures[job_id]

    def _run(self, job_id: str, fn: Callable[..., Any], args: tuple) -> None:
        self._store.update_job(job_id, "running")
        try:
            result = fn(*args)
            self._store.update_job(job_id, "done", result=result)
        except Exception as exc:
            self._mark_failed(job_id, str(exc))

    def _mark_failed(self, job_id: str, error: str) -> None:
        try:
            self._store.update_job(job_id, "failed", error=error)
        except BaseException:
            log.exception("could not mark job %s failed", job_id)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True)
