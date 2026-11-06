"""Library-wide commands against the running API: regen-all, fix-all, findings, jobs-wait."""

import argparse
import os
import sys
import time
from collections.abc import Callable

import httpx

from saber_tooth.tls import client_verify

# SABER_API overrides the default; an https URL with the self-signed cert
# also needs SABER_TLS_VERIFY=0.
DEFAULT_API = os.environ.get("SABER_API") or "http://127.0.0.1:8100"
MAP_CAP = 30


def _call(method: str, path: str, api: str, transport: httpx.BaseTransport | None) -> dict:
    with httpx.Client(transport=transport, timeout=60, verify=client_verify(api)) as client:
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


def map_lines(
    api: str, transport: httpx.BaseTransport | None = None, cap: int = MAP_CAP
) -> list[str]:
    """One line per map with findings: rule counts and unfixed reason, capped at `cap`."""
    items: list[dict] = []
    seen = 0
    while True:
        q = f"/api/maps?limit=100&offset={seen}"
        page = _call("GET", q, api, transport)
        seen += len(page["items"])
        items += [m for m in page["items"] if m.get("errors", 0) + m.get("warnings", 0) > 0]
        if not page["items"] or seen >= page["total"]:
            break
    rows, unanalysed = [], 0
    for m in items[:cap]:
        info = _call("GET", f"/api/maps/{m['id']}/findings", api, transport)
        found = info["findings"]
        rules: dict[str, int] = {}
        for f in found:
            rules[f["rule"]] = rules.get(f["rule"], 0) + 1
        reason = next((f["unfixed_reason"] for f in found if f.get("unfixed_reason")), "-")
        counts = ",".join(f"{r}:{n}" for r, n in sorted(rules.items()))
        tail = " hidden-original" if m.get("fixed_copy_id") else ""
        if info.get("unanalysed"):
            tail += " unanalysed"
            unanalysed += 1
        rows.append(f"{m['folder']} {m['id']} {counts} reason={reason}{tail}")
    if len(items) > cap:
        rows.append(f"... {len(items) - cap} more")
    if unanalysed:
        rows.append(f"{unanalysed} unanalysed")
    return rows


def _findings_cmd(a) -> int:
    return _run(lambda: findings_lines(a.api) + (map_lines(a.api) if a.maps else []))


def _run(fn) -> int:
    try:
        out = fn()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("\n".join(out) if isinstance(out, list) else out)
    return 0


def _counts(jobs: dict, kind: str | None) -> tuple[dict[str, int], list[dict]]:
    """Per-status counts of the listed jobs (of one kind when given) and the failed ones."""
    rows = [r for k in ("running", "queued", "recent") for r in jobs.get(k, [])]
    rows = [r for r in rows if kind is None or r.get("kind") == kind]
    states = ("queued", "running", "done", "failed")
    counts = {s: sum(r.get("status") == s for r in rows) for s in states}
    return counts, [r for r in rows if r.get("status") == "failed"]


def _line(c: dict[str, int]) -> str:
    return f"queued {c['queued']} running {c['running']} done {c['done']} failed {c['failed']}"


def jobs_wait(
    api: str,
    kind: str | None = None,
    poll: float = 15,
    timeout: float = 0,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    out: Callable[[str], None] = print,
) -> int:
    """Poll /api/jobs until none is queued or running; 0 ok, 1 some failed, 3 timeout."""
    start, last = clock(), None
    while True:
        counts, failed = _counts(_call("GET", "/api/jobs", api, transport), kind)
        line = _line(counts)
        if line != last:
            out(line)
            last = line
        if not counts["queued"] and not counts["running"]:
            break
        if timeout and clock() - start >= timeout:
            out(f"timeout after {timeout:g}s: {line}")
            return 3
        sleep(poll)
    for row in failed[:7]:
        out(f"failed {row.get('title') or row.get('map_id')}: {str(row.get('error'))[:160]}")
    if len(failed) > 7:
        out(f"... {len(failed) - 7} more failed")
    out(f"total {sum(counts.values())} {line}")
    return 1 if failed else 0


def _wait_cmd(a) -> int:
    try:
        return jobs_wait(a.api, a.kind, a.poll, a.timeout)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def register(sub) -> None:
    """Add the subcommands to the CLI's subparsers."""
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
            _findings_cmd,
        ),
    ):
        p: argparse.ArgumentParser = sub.add_parser(name, help=help_)
        p.add_argument("--api", default=DEFAULT_API)
        if name == "findings":
            p.add_argument("--maps", action="store_true", help="list maps with findings")
        p.set_defaults(func=func)
    p = sub.add_parser("jobs-wait", help="wait until no job is queued or running")
    p.add_argument("--api", default=DEFAULT_API)
    p.add_argument("--kind", default=None)
    p.add_argument("--poll", type=float, default=15)
    p.add_argument("--timeout", type=float, default=0)
    p.set_defaults(func=_wait_cmd)
