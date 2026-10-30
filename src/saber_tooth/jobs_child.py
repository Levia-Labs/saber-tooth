"""Run one job's handler in a spawned worker process, bridged to the parent by a pipe.

The parent stays the only writer of job rows: the child sends progress, then one final
message (done, cancelled or failed) over a pipe, and a parent-side thread writes it to the
store. Cancellation travels the other way through a multiprocessing Event the handler's
`progress.check()` reads. The child rebuilds its service from `factory` (a picklable callable
returning `{kind: handler}`) and opens its own SQLite connection there; nothing live crosses
the process boundary. See docs/adr/0013-worker-processes-for-parallel-jobs.md.
"""

import multiprocessing
import threading
from collections.abc import Callable
from typing import Any

from saber_tooth.jobs_errors import JobCancelled, JobFailed, error_text

POLL_S = 0.1
BUSY_TIMEOUT_MS = 30_000  # a child waits this long for another writer before failing
# PRAGMA takes no bound parameters, so the statement is a constant rather than a formatted string.
BUSY_TIMEOUT_SQL = "PRAGMA busy_timeout=30000"
CHILD_GRACE_S = 5.0  # how long a finished child may take to exit before it is killed

Factory = Callable[[], dict[str, Callable[[dict, Any], Any]]]


class ChildProgress:
    """The progress object inside the child: reports over the pipe, checks the cancel event."""

    def __init__(self, conn, cancel) -> None:
        self._conn, self._cancel = conn, cancel
        self._send_lock = threading.Lock()

    def check(self) -> None:
        if self._cancel.is_set():
            raise JobCancelled

    def __call__(self, text: str) -> None:
        self.check()
        with self._send_lock:
            self._conn.send(("progress", text))


def child_main(factory: Factory, kind: str, args: dict, conn, cancel) -> None:
    """Entry point of the worker process; every outcome becomes one pipe message."""
    progress = ChildProgress(conn, cancel)
    try:
        progress.check()
        result = factory()[kind](args, progress)
        message: tuple = ("done", result)
    except JobCancelled:
        message = ("cancelled",)
    except Exception as exc:
        message = ("failed", error_text(exc), getattr(exc, "result", None))
    try:
        conn.send(message)
    except Exception as exc:  # a result that cannot be pickled still has to end the job
        conn.send(("failed", f"job result could not be sent: {exc}", None))
    finally:
        conn.close()


def _died(proc) -> JobFailed:
    proc.join(CHILD_GRACE_S)  # the pipe closes a moment before the exit code is available
    return JobFailed(f"worker process exited unexpectedly (code {proc.exitcode})")


class ChildRunner:
    def __init__(self, factory: Factory, kinds: frozenset[str]) -> None:
        self.factory, self.kinds = factory, kinds
        self._ctx = multiprocessing.get_context("spawn")

    def run(
        self,
        kind: str,
        args: dict,
        on_progress: Callable[[str], None],
        cancelled: Callable[[], bool],
    ) -> Any:
        """Run the job in a fresh process; returns the result or raises JobCancelled/JobFailed."""
        receiver, sender = self._ctx.Pipe(duplex=False)
        cancel = self._ctx.Event()
        proc = self._ctx.Process(
            target=child_main, args=(self.factory, kind, args, sender, cancel), daemon=True
        )
        proc.start()
        sender.close()  # the parent's copy, so a dead child shows as EOF
        try:
            return self._watch(proc, receiver, cancel, on_progress, cancelled)
        finally:
            cancel.set()  # a watcher that failed must not leave the child running
            receiver.close()
            proc.join(CHILD_GRACE_S)
            if proc.is_alive():
                proc.kill()
                proc.join()

    @staticmethod
    def _watch(proc, receiver, cancel, on_progress, cancelled) -> Any:
        while True:
            if cancelled():
                cancel.set()
            try:
                if not receiver.poll(POLL_S):
                    if proc.is_alive():
                        continue
                    if not receiver.poll(0):
                        raise _died(proc)
                message = receiver.recv()
            except (EOFError, OSError):
                raise _died(proc) from None
            if message[0] == "progress":
                on_progress(message[1])
            elif message[0] == "done":
                return message[1]
            elif message[0] == "cancelled":
                raise JobCancelled
            else:
                raise JobFailed(message[1], message[2])


def share_store(store) -> None:
    """Let several processes write one SQLite file: write-ahead log, long busy wait."""
    with store._lock:
        store._db.execute("PRAGMA journal_mode=WAL")
        store._db.execute(BUSY_TIMEOUT_SQL)
