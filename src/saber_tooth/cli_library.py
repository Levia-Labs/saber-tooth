"""Library-wide commands against the running API: regen-all, fix-all, findings."""

import argparse
import sys

import httpx

DEFAULT_API = "http://127.0.0.1:8100"


def _call(method: str, path: str, api: str, transport: httpx.BaseTransport | None) -> dict:
    with httpx.Client(transport=transport, timeout=60) as client:
        resp = client.request(method, f"{api.rstrip('/')}{path}")
        resp.raise_for_status()
        data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"unexpected response: {str(data)[:80]}")
    return data


def queue_bulk(path: str, api: str, transport: httpx.BaseTransport | None = None) -> str:
    """Post a bulk route and return one line: the count of queued jobs."""
    data = _call("POST", path, api, transport)
    if not isinstance(data.get("count"), int):
        raise ValueError(f"unexpected response: {str(data)[:80]}")
    return f"queued {data['count']} jobs"


def findings_lines(api: str, transport: httpx.BaseTransport | None = None) -> list[str]:
    """The library findings summary as one line per rule and severity."""
    data = _call("GET", "/api/findings/summary", api, transport)
    maps = data["maps"]
    head = (
        f"{maps['total']} maps, {maps['scanned']} scanned, "
        f"{maps['with_findings']} with findings, {data['findings']} findings"
    )
    rows = [
        f"{r['findings']:>6}  {r['severity']:<7} {r['rule']}  ({r['maps']} maps)"
        for r in data["rules"]
    ]
    return [head, *rows]


def _run(fn) -> int:
    try:
        out = fn()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("\n".join(out) if isinstance(out, list) else out)
    return 0


def register(sub) -> None:
    """Add the three subcommands to the CLI's subparsers."""
    for name, help_, func in (
        (
            "regen-all",
            "queue a regenerate job for every generated map",
            lambda a: _run(lambda: queue_bulk("/api/maps/regenerate-all", a.api)),
        ),
        (
            "fix-all",
            "queue a fix job for every map with open findings",
            lambda a: _run(lambda: queue_bulk("/api/maps/fix-all", a.api)),
        ),
        (
            "findings",
            "show library finding counts per rule and severity",
            lambda a: _run(lambda: findings_lines(a.api)),
        ),
    ):
        p: argparse.ArgumentParser = sub.add_parser(name, help=help_)
        p.add_argument("--api", default=DEFAULT_API)
        p.set_defaults(func=func)
