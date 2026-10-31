"""Wait for the service's background re-index and copy-scan backfill to go idle."""

import time


def settle(svc, timeout: float = 15.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        with svc._bg_lock:
            idle = not (svc._reindexing or svc._backfilling or svc._pending_scans)
        if idle:
            return
        time.sleep(0.02)
    raise AssertionError("background work did not finish")
