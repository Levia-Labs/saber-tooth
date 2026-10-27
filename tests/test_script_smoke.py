"""Tests for scripts/smoke.py with an in-memory fetch; no network, no Docker."""

import json

from tests.script_loader import load

smoke = load("smoke")

INDEX = b'<html><script src="/assets/app.js"></script><link href="/assets/app.css"></html>'
PAGE = {"items": [{"cover_url": "/api/maps/1/cover"}], "total": 3}
TOOLS = {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "list_maps"}]}}


def make_fetch(overrides=None):
    routes = {
        "/": (200, "text/html", INDEX),
        "/maps/x": (200, "text/html", INDEX),
        "/new": (200, "text/html", INDEX),
        "/assets/app.js": (200, "text/javascript", b"x"),
        "/assets/app.css": (200, "text/css", b"x"),
        "/api/maps?limit=5": (200, "application/json", json.dumps(PAGE).encode()),
        "/api/maps/facets": (200, "application/json", b'{"total": 3}'),
        "/api/maps/1/cover": (200, "image/jpeg", b"x"),
        "/mcp": (200, "text/event-stream", b"data: " + json.dumps(TOOLS).encode()),
    }
    routes.update(overrides or {})

    def fetch(url, body=None):
        return routes.get(url.removeprefix("http://h"), (404, "", b""))

    return fetch


def test_asset_urls_dedupes_and_sorts():
    assert smoke.asset_urls(INDEX.decode()) == ["/assets/app.css", "/assets/app.js"]


def test_parse_mcp_json_sse_and_garbage():
    raw = json.dumps(TOOLS).encode()
    assert smoke.parse_mcp(raw) == [{"name": "list_maps"}]
    assert smoke.parse_mcp(b"event: message\ndata: " + raw) == [{"name": "list_maps"}]
    assert smoke.parse_mcp(b"nope") == []


def test_all_checks_pass():
    results = smoke.run_checks("http://h", make_fetch())
    assert all(ok for _, ok, _ in results)
    names = [n for n, _, _ in results]
    assert {"api maps", "api facets", "cover", "mcp tools/list", "asset /assets/app.js"} <= set(
        names
    )


def test_failures_are_reported():
    fetch = make_fetch({"/assets/app.js": (404, "", b""), "/mcp": (200, "application/json", b"{}")})
    failed = {n for n, ok, _ in smoke.run_checks("http://h", fetch) if not ok}
    assert failed == {"asset /assets/app.js", "mcp tools/list"}


def test_bad_maps_shape_fails():
    fetch = make_fetch({"/api/maps?limit=5": (200, "application/json", b"[]")})
    failed = {n for n, ok, _ in smoke.run_checks("http://h", fetch) if not ok}
    assert "api maps" in failed


def test_wait_ready_retries_then_times_out():
    calls = []

    def fetch(url, body=None):
        calls.append(url)
        return (200, "", b"") if len(calls) >= 3 else (0, "", b"")

    assert smoke.wait_ready("http://h", 100, fetch, sleep=lambda s: None)
    assert not smoke.wait_ready("http://h", 0, lambda u, b=None: (0, "", b""), sleep=lambda s: None)


def test_default_base_reads_env(tmp_path):
    env = tmp_path / ".env"
    env.write_text("LEVELS_DIR=x\nSABER_PORT=9000\n", encoding="utf-8")
    assert smoke.default_base(env) == "http://127.0.0.1:9000"
    assert smoke.default_base(tmp_path / "missing") == "http://127.0.0.1:8100"


def test_compose_health_starting_is_not_ready(monkeypatch):
    rows = '{"Service": "s", "State": "running", "Health": "starting"}\n'

    class Res:
        returncode = 0
        stdout = rows

    monkeypatch.setattr(smoke.subprocess, "run", lambda *a, **k: Res())
    ok, detail = smoke.compose_health()
    assert not ok and "starting=s" in detail


def test_wait_health_polls_until_healthy():
    seq = iter([(False, "bad=none starting=s"), (False, "bad=none starting=s"), (True, "ok")])
    sleeps = []
    assert smoke.wait_health(100, lambda: next(seq), sleeps.append) == (True, "ok")
    assert len(sleeps) == 2


def test_wait_health_fails_fast_on_unhealthy_and_times_out():
    calls = []

    def bad():
        calls.append(1)
        return False, "bad=s"

    assert not smoke.wait_health(100, bad, lambda s: None)[0] and len(calls) == 1
    assert not smoke.wait_health(0, lambda: (False, "starting=s"), lambda s: None)[0]
