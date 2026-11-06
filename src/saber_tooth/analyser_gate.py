"""Bounded concurrency for analyser requests, shared by threads and worker processes.

The slots are lock files in a writable folder every worker shares, under DATA_DIR in the service
(one per allowed in-flight analysis; the uploads mount is read-only); an OS file
lock is held while a request runs, so a worker process or thread that finds every slot taken
waits, polling the cancel flag, and the lock vanishes with a crashed holder.
"""

import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt

POLL_S = 0.1
DEFAULT_SLOTS = 1


def slots_from_env() -> int:
    try:
        return max(1, int(os.environ.get("ANALYSER_CONCURRENCY", DEFAULT_SLOTS)))
    except ValueError:
        return DEFAULT_SLOTS


def _try_lock(fd: int) -> bool:
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def _unlock(fd: int) -> None:
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
        else:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except OSError:
        pass


@contextmanager
def analyser_slot(
    folder: Path, slots: int, cancel: Callable[[], None] | None = None
) -> Iterator[None]:
    """Hold one of `slots` analyser slots; waits (calling `cancel`) while all are taken."""
    folder.mkdir(parents=True, exist_ok=True)
    while True:
        for i in range(slots):
            fd = os.open(folder / f".analyser-slot-{i}.lock", os.O_RDWR | os.O_CREAT)
            if _try_lock(fd):
                try:
                    yield
                finally:
                    _unlock(fd)
                    os.close(fd)
                return
            os.close(fd)
        if cancel is not None:
            cancel()
        time.sleep(POLL_S)
