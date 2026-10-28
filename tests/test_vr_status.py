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
