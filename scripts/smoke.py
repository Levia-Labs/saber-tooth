"""Smoke-check a running saber-tooth stack; one line per check and a final PASS or FAIL.

Waits for /api/maps, then checks the SPA routes, referenced assets, the maps API, facets, a
cover, the MCP tools/list and the compose service health. Read-only (the only POST is the
MCP JSON-RPC tools/list).

Usage: uv run python scripts/smoke.py [--base URL] [--timeout S]
"""

import argparse
import json
import re
import subprocess  # nosec B404 - fixed docker argv, no shell
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

Response = tuple[int, str, bytes]
Fetch = Callable[[str, bytes | None], Response]
ASSET_RE = re.compile(r"""(?:src|href)=["'](/[^"']+\.(?:js|css|mjs|svg|png|ico|woff2?))["']""")
MCP_BODY = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()


def default_base(env_file: Path = Path(".env")) -> str:
    port = "8100"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("SABER_PORT="):
                port = line.split("=", 1)[1].strip().strip("\"'") or port
    return f"http://127.0.0.1:{port}"


def http(url: str, body: bytes | None = None) -> Response:
    """GET (or JSON POST when body is set); never raises on HTTP errors, status 0 on failure."""
    if not url.startswith(("http://", "https://")):
        return 0, "", b""
    headers = {"Accept": "application/json, text/event-stream, */*"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)  # noqa: S310  # nosec B310
    try:
        # nosemgrep: dynamic-urllib-use-detected - scheme checked above
        with urllib.request.urlopen(req, timeout=10) as res:  # noqa: S310  # nosec B310
            return res.status, res.headers.get("Content-Type", ""), res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), b""
    except (urllib.error.URLError, OSError):
        return 0, "", b""


def wait_ready(base: str, timeout: float, fetch: Fetch = http, sleep=time.sleep) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        if fetch(f"{base}/api/maps?limit=1", None)[0] == 200:
            return True
        if time.monotonic() >= deadline:
            return False
        sleep(2)


def asset_urls(html: str) -> list[str]:
    return sorted(set(ASSET_RE.findall(html)))


def parse_mcp(body: bytes) -> list:
    """Tools from a JSON or SSE `tools/list` answer; empty list when malformed."""
    text = body.decode("utf-8", errors="replace").strip()
    data = [ln[5:].strip() for ln in text.splitlines() if ln.startswith("data:")]
    try:
        return json.loads(data[-1] if data else text)["result"]["tools"]
    except (ValueError, KeyError, TypeError, IndexError):
        return []


def run_checks(base: str, fetch: Fetch = http) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    html = ""
    for route in ("/", "/maps/x", "/new", "/vr", "/vr/maps/x", "/vr/beatsaver"):
        status, ctype, body = fetch(base + route, None)
        add(f"html {route}", status == 200 and "html" in ctype, f"{status} {ctype}")
        if route == "/":
            html = body.decode("utf-8", errors="replace")
    for url in asset_urls(html):
        add(f"asset {url}", fetch(base + url, None)[0] == 200)
    status, _, body = fetch(f"{base}/api/maps?limit=5", None)
    try:
        page = json.loads(body)
        ok = status == 200 and isinstance(page["items"], list) and isinstance(page["total"], int)
        add("api maps", ok, f"total={page['total']} items={len(page['items'])}")
    except (ValueError, KeyError, TypeError):
        page = {"items": []}
        add("api maps", False, f"{status} bad shape")
    status, _, body = fetch(f"{base}/api/maps/facets", None)
    add("api facets", status == 200 and b'"total"' in body, str(status))
    status, _, body = fetch(f"{base}/api/vr/status", None)
    add("api vr status", status == 200 and b'"source"' in body, str(status))
    cover = next((i["cover_url"] for i in page["items"] if i.get("cover_url")), None)
    if cover:
        status, ctype, _ = fetch(base + cover, None)
        add("cover", status == 200 and ctype.startswith("image/"), f"{status} {ctype}")
    else:
        add("cover", True, "skipped, no map with a cover")
    status, _, body = fetch(f"{base}/mcp", MCP_BODY)
    tools = parse_mcp(body)
    add("mcp tools/list", status == 200 and bool(tools), f"{status} tools={len(tools)}")
    return results


def compose_health() -> tuple[bool, str]:
    try:
        res = subprocess.run(  # nosec B603 B607 - constant argv, no shell
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            check=False,
            encoding="utf-8",
        )
    except OSError:
        return False, "docker not found"
    if res.returncode:
        return False, "docker compose ps failed"
    rows = [json.loads(ln) for ln in res.stdout.splitlines() if ln.strip().startswith("{")]
    bad = [r.get("Service", "?") for r in rows if r.get("State") != "running"]
    bad += [r.get("Service", "?") for r in rows if r.get("Health") == "unhealthy"]
    starting = [r.get("Service", "?") for r in rows if r.get("Health") == "starting"]
    detail = f"services={len(rows)} bad={','.join(bad) or 'none'}"
    if starting:
        detail += f" starting={','.join(starting)}"
    return bool(rows) and not bad and not starting, detail


def wait_health(
    timeout: float, check: Callable[[], tuple[bool, str]] = compose_health, sleep=time.sleep
) -> tuple[bool, str]:
    """Poll compose health while a service is still `starting`; other failures return at once."""
    deadline = time.monotonic() + timeout
    while True:
        ok, detail = check()
        if ok or "starting=" not in detail or time.monotonic() >= deadline:
            return ok, detail
        sleep(3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default=None, help="base URL (default from SABER_PORT in .env)")
    parser.add_argument("--timeout", type=float, default=60, help="seconds to wait for the API")
    args = parser.parse_args(argv)
    base = (args.base or default_base()).rstrip("/")
    if not wait_ready(base, args.timeout):
        print(f"FAIL wait {base}/api/maps not ready after {args.timeout:.0f}s")
        return 1
    results = run_checks(base)
    ok, detail = wait_health(args.timeout)
    results.append(("compose health", ok, detail))
    for name, passed, info in results:
        print(f"{'ok  ' if passed else 'FAIL'} {name} {info}".rstrip())
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f"smoke: {'FAIL' if failed else 'PASS'} ({failed} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
