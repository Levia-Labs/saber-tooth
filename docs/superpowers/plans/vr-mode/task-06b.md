# Task 6: Backend status client (part b)

Continues [task-06a.md](task-06a.md).

- [ ] **Step 4: Implement**

Create `src/saber_tooth/api/vr_status.py`:

```python
"""GET /api/vr/status: the headset runtime from the host helper, or probed in-process."""

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from saber_tooth.vr.model import Probe, none_status, status_dict
from saber_tooth.vr.probe import probe
from saber_tooth.vr.readers import default_readers, detect_os
from saber_tooth.vr.worn import WornMonitor, load_openvr

log = logging.getLogger(__name__)

DEFAULT_URL = "http://host.docker.internal:8101/status"
TIMEOUT_S = 0.3
CACHE_S = 2.0
LOG_EVERY_S = 60.0
MAX_BYTES = 4096

_monitor = WornMonitor(load_openvr, log.info)


def in_container() -> bool:
    return Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


def fetch_json(url: str, timeout: float = TIMEOUT_S) -> object:
    """GET `url` and parse the JSON; one deadline covers the whole answer, not each read."""
    deadline = time.monotonic() + timeout
    chunks: list[bytes] = []
    size = 0
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=False) as res:
        res.raise_for_status()
        for chunk in res.iter_bytes():
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("the helper's answer is too large")
            if time.monotonic() > deadline:
                raise TimeoutError("the helper's answer was too slow")
            chunks.append(chunk)
    return json.loads(b"".join(chunks))


def _text(value: object, limit: int) -> str | None:
    return value[:limit] if isinstance(value, str) else None


def clean_status(raw: object) -> dict | None:
    """The helper's answer in the documented shape, or None when it is not that shape."""
    if not isinstance(raw, dict):
        return None
    runtimes, xr, worn = raw.get("runtimes"), raw.get("xr_runtime"), raw.get("worn")
    if not isinstance(runtimes, list) or not all(isinstance(r, str) for r in runtimes):
        return None
    if xr is not None and not isinstance(xr, str):
        return None
    if worn is not None and not isinstance(worn, bool):
        return None
    os_name = _text(raw.get("os"), 40) or "unknown"
    return status_dict(os_name, Probe(runtimes, _text(xr, 200)), worn)


def local_status() -> dict:
    """Probe this machine in-process, for a backend that runs natively."""
    os_name = detect_os()
    found = probe(os_name, default_readers(os_name))
    return status_dict(os_name, found, _monitor.read("SteamVR" in found.runtimes))


class VrStatusClient:
    def __init__(
        self,
        url: str | None = None,
        native: bool | None = None,
        local: Callable[[], dict] | None = None,
        fetch: Callable[[str, float], object] = fetch_json,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.url = url or os.environ.get("VR_AGENT_URL") or DEFAULT_URL
        self._native = (not in_container()) if native is None else native
        self._local = local or local_status
        self._fetch = fetch
        self._clock = clock
        self._lock = threading.Lock()
        self._cached: tuple[float, dict] | None = None
        self._last_log = float("-inf")

    def status(self) -> dict:
        """The cached answer while it is under two seconds old; failures are cached too."""
        with self._lock:
            now = self._clock()
            if self._cached is not None and now - self._cached[0] < CACHE_S:
                return self._cached[1]
            value = self._read(now)
            self._cached = (self._clock(), value)
            return value

    def _read(self, now: float) -> dict:
        try:
            if self._native:
                return {**self._local(), "source": "local"}
            clean = clean_status(self._fetch(self.url, TIMEOUT_S))
            if clean is None:
                raise ValueError("the helper answered something other than the status shape")
            return {**clean, "source": "agent"}
        except Exception as exc:
            self._note(now, exc)
            return {**none_status(), "source": "none"}

    def _note(self, now: float, exc: Exception) -> None:
        if now - self._last_log >= LOG_EVERY_S:
            self._last_log = now
            log.warning("vr status unavailable (%s): %s", self.url, exc)
```

- [ ] **Step 5: Run it to see it pass**

Run: `rtk proxy uv run pytest -q tests/test_vr_status.py`
Expected: PASS, 25 passed.

- [ ] **Step 6: Lint the new module**

Run: `rtk proxy uv run ruff check src/saber_tooth/api/vr_status.py tests/vr_fake_agent.py tests/test_vr_status.py`
Expected: no findings.

- [ ] **Step 7: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): backend status client with timeout, cache and in-process mode" src/saber_tooth/api/vr_status.py tests/vr_fake_agent.py tests/test_vr_status.py`
