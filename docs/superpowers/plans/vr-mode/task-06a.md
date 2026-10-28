# Task 6: Backend status client (part a: fake helper and failing tests)

`VrStatusClient` answers `GET /api/vr/status`. In a container it calls the helper at `VR_AGENT_URL` (default `http://host.docker.internal:8101/status`); run natively it probes in-process. The timeout is 300 ms, the answer, a failure included, is cached for 2 s so a missing helper costs one 300 ms wait per 2 s, and any failure returns the same shape with no runtime and `source: "none"`. The helper's answer is validated before it is trusted: anything that is not the documented shape, or larger than 4 KiB, counts as the helper being down. At most one log line per minute.

**Files:**

- Create: `src/saber_tooth/api/vr_status.py`
- Create: `tests/vr_fake_agent.py`
- Test: `tests/test_vr_status.py`

**Interfaces:**

Consumes: `RUNTIME_ORDER`, `Probe`, `none_status`, `status_dict` (`vr/model.py`), `probe` (`vr/probe.py`), `default_readers`, `detect_os` (`vr/readers.py`), `WornMonitor`, `load_openvr` (`vr/worn.py`); `httpx` (existing dependency).

Produces (`api/vr_status.py`):

1. `DEFAULT_URL = "http://host.docker.internal:8101/status"`, `TIMEOUT_S = 0.3`, `CACHE_S = 2.0`, `LOG_EVERY_S = 60.0`, `MAX_BYTES = 4096`.
2. `in_container() -> bool`: `/.dockerenv` or `/run/.containerenv` exists.
3. `fetch_json(url: str, timeout: float = TIMEOUT_S) -> object`: GET with a total deadline of `timeout`; raises on a bad status, a body over `MAX_BYTES`, bad JSON or a missed deadline.
4. `clean_status(raw: object) -> dict | None`: the documented shape rebuilt through `status_dict` (so `runtimes` is filtered and ordered, `runtime` recomputed), or None when `raw` is not an object of that shape.
5. `local_status() -> dict`: the in-process probe in the documented shape.
6. `VrStatusClient(url: str | None = None, native: bool | None = None, local: Callable[[], dict] | None = None, fetch: Callable[[str, float], object] = fetch_json, clock: Callable[[], float] = time.monotonic)` with `url` (attribute) and `status() -> dict` (the documented shape plus `source`: `"agent"`, `"local"` or `"none"`). `url` defaults to the `VR_AGENT_URL` environment variable when set and non-empty, else `DEFAULT_URL`; `native` defaults to `not in_container()`.

Produces (`tests/vr_fake_agent.py`): `FakeAgent(body: object = None, delay: float = 0.0, code: int = 200, raw: bytes | None = None)`, a context manager that serves `GET /status` on a loopback port: `url`, `hits`. `raw` replaces the JSON body.

- [ ] **Step 1: Write the fake helper**

Create `tests/vr_fake_agent.py`:

```python
"""A loopback HTTP server that plays the host helper: scripted body, delay and status code."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeAgent:
    """Context manager; `url` is the /status address, `hits` counts requests received."""

    def __init__(self, body=None, delay=0.0, code=200, raw=None):
        self.body, self.delay, self.code, self.raw = body, delay, code, raw
        self.hits = 0
        agent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                agent.hits += 1
                time.sleep(agent.delay)
                data = agent.raw if agent.raw is not None else json.dumps(agent.body).encode()
                try:
                    self.send_response(agent.code)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except OSError:
                    return  # the client gave up (a timeout): nothing to tell it

            def log_message(self, format, *args):
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}/status"

    def __enter__(self):
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_vr_status.py`:

```python
"""The backend status client: proxy, timeout, cache, validation, local mode and logging."""

import logging
import time

import pytest
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.api import vr_status
from saber_tooth.api.vr_status import DEFAULT_URL, VrStatusClient, clean_status
from saber_tooth.vr.model import RUNTIME_ORDER, Probe, status_dict
from tests.vr_fake_agent import FakeAgent

AGENT = {
    "os": "windows",
    "runtime": "Oculus",
    "runtimes": ["Oculus", "SteamVR"],
    "xr_runtime": "Oculus",
    "worn": False,
}
NONE = {"os": "unknown", "runtime": None, "runtimes": [], "xr_runtime": None, "worn": None}


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def down(url, timeout):
    raise OSError("connection refused")


def test_the_helper_answer_is_proxied_with_the_spec_order_and_source_agent():
    with FakeAgent(AGENT) as agent:
        got = VrStatusClient(url=agent.url, native=False).status()
    assert got == {
        **AGENT,
        "runtime": "SteamVR",
        "runtimes": ["SteamVR", "Oculus"],
        "source": "agent",
    }


def test_a_helper_that_is_not_running_gives_the_none_shape():
    with FakeAgent(AGENT) as agent:
        url = agent.url
    assert VrStatusClient(url=url, native=False).status() == {**NONE, "source": "none"}


def test_a_slow_helper_is_given_up_on_after_the_timeout():
    with FakeAgent(AGENT, delay=1.5) as agent:
        started = time.monotonic()
        got = VrStatusClient(url=agent.url, native=False).status()
        elapsed = time.monotonic() - started
    assert got["source"] == "none" and got["runtime"] is None
    assert elapsed < 1.2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"body": []},
        {"body": "SteamVR"},
        {"body": None},
        {"body": {"runtimes": "SteamVR"}},
        {"body": {"runtimes": [1, 2]}},
        {"body": {"runtimes": [], "worn": "yes"}},
        {"body": {"runtimes": [], "xr_runtime": 5}},
        {"body": {"runtime": "SteamVR"}},
        {"raw": b"not json at all"},
        {"raw": b""},
        {"raw": b'{"runtimes": []' + b" " * 5000 + b"}"},
        {"body": AGENT, "code": 500},
        {"body": AGENT, "code": 404},
    ],
)
def test_malformed_agent_answers_count_as_down(kwargs):
    with FakeAgent(**kwargs) as agent:
        got = VrStatusClient(url=agent.url, native=False).status()
    assert got == {**NONE, "source": "none"}


def test_the_answer_is_cached_for_two_seconds():
    clock = Clock()
    with FakeAgent(AGENT) as agent:
        client = VrStatusClient(url=agent.url, native=False, clock=clock)
        first = client.status()
        clock.now += 1.9
        assert client.status() == first and agent.hits == 1
        clock.now += 0.2
        client.status()
        assert agent.hits == 2


def test_a_failed_probe_is_cached_for_two_seconds_too():
    clock, calls = Clock(), []

    def fetch(url, timeout):
        calls.append(url)
        raise OSError("down")

    client = VrStatusClient(url="http://h/status", native=False, fetch=fetch, clock=clock)
    assert client.status()["source"] == "none" and client.status()["source"] == "none"
    assert len(calls) == 1
    clock.now += 2.1
    client.status()
    assert len(calls) == 2


def test_the_fetch_is_given_the_300_ms_timeout():
    seen = []

    def fetch(url, timeout):
        seen.append(timeout)
        return AGENT

    VrStatusClient(url="http://h/status", native=False, fetch=fetch).status()
    assert seen == [0.3] and vr_status.TIMEOUT_S == 0.3 and vr_status.CACHE_S == 2.0


def test_native_mode_probes_in_process_and_never_calls_the_helper():
    def fetch(url, timeout):
        raise AssertionError("native mode must not call the helper")

    def local():
        return status_dict("linux", Probe(["Monado"], "Monado"), None)

    got = VrStatusClient(native=True, local=local, fetch=fetch).status()
    assert got["source"] == "local" and got["runtime"] == "Monado" and got["os"] == "linux"


def test_a_local_probe_that_raises_gives_the_none_shape():
    def local():
        raise RuntimeError("probe broke")

    assert VrStatusClient(native=True, local=local).status() == {**NONE, "source": "none"}


def test_the_url_comes_from_the_environment_else_the_default(monkeypatch):
    monkeypatch.delenv("VR_AGENT_URL", raising=False)
    assert VrStatusClient().url == DEFAULT_URL == "http://host.docker.internal:8101/status"
    monkeypatch.setenv("VR_AGENT_URL", "")
    assert VrStatusClient().url == DEFAULT_URL
    monkeypatch.setenv("VR_AGENT_URL", "http://10.0.0.5:9000/status")
    assert VrStatusClient().url == "http://10.0.0.5:9000/status"


def test_at_most_one_log_line_per_minute(caplog):
    clock = Clock()
    client = VrStatusClient(url="http://h/status", native=False, fetch=down, clock=clock)
    with caplog.at_level(logging.INFO, logger=vr_status.log.name):
        for _ in range(5):
            client.status()
            clock.now += 2.1  # past the cache each time, still inside one minute
        assert len(caplog.records) == 1
        clock.now += 60
        client.status()
        assert len(caplog.records) == 2


def test_clean_status_keeps_only_known_runtimes_in_order():
    raw = {"os": "linux", "runtimes": ["ALVR", "Bogus", "SteamVR"], "worn": True}
    assert clean_status(raw) == {
        "os": "linux",
        "runtime": "SteamVR",
        "runtimes": ["SteamVR", "ALVR"],
        "xr_runtime": None,
        "worn": True,
    }


KEYS = st.sampled_from(["os", "runtime", "runtimes", "xr_runtime", "worn", "x"])
JSON = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.text(max_size=20)
    | st.sampled_from(RUNTIME_ORDER),
    lambda inner: st.lists(inner, max_size=4) | st.dictionaries(KEYS, inner, max_size=5),
    max_leaves=12,
)


@given(JSON)
def test_clean_status_never_raises_and_only_returns_the_documented_shape(raw):
    out = clean_status(raw)
    if out is None:
        return
    assert set(out) == {"os", "runtime", "runtimes", "xr_runtime", "worn"}
    assert out["runtime"] in (None, *RUNTIME_ORDER)
    assert out["runtimes"] == [n for n in RUNTIME_ORDER if n in out["runtimes"]]
    assert out["worn"] in (None, True, False)
    assert (out["runtime"] is None) == (out["runtimes"] == [])
```

- [ ] **Step 3: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_vr_status.py`
Expected: FAIL: `ImportError: cannot import name 'vr_status' from 'saber_tooth.api'`.

Continued in [task-06b.md](task-06b.md).
