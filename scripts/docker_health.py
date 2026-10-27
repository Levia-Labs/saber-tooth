"""Per compose service: state, health and, when unhealthy or exited, probe output and logs.

Read-only: `docker compose ps`, `docker inspect` and `docker compose logs`.

Usage: uv run python scripts/docker_health.py [--lines N]
"""

import argparse
import json
import subprocess  # nosec B404 - fixed docker argv, no shell
import sys
from collections.abc import Callable

Run = Callable[..., str | None]
BAD_STATES = {"exited", "dead", "restarting", "paused", "created"}


def docker(*args: str) -> str | None:
    """Run docker; stdout, or None when docker is missing or the command fails."""
    try:
        res = subprocess.run(  # nosec B603 B607 - constant argv, no shell, docker from PATH
            ["docker", *args], capture_output=True, check=False, encoding="utf-8"
        )
    except OSError:
        return None
    return res.stdout if res.returncode == 0 else None


def parse_ps(text: str) -> list[dict]:
    """Rows from `docker compose ps -a --format json` (JSON lines or one array)."""
    text = text.strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def is_bad(row: dict) -> bool:
    return row.get("State", "") in BAD_STATES or row.get("Health", "") == "unhealthy"


def probe_output(inspect_json: str | None, count: int = 3) -> list[str]:
    """Last health probe outputs from `docker inspect` JSON, newest last."""
    if not inspect_json:
        return []
    try:
        log = json.loads(inspect_json)[0]["State"]["Health"]["Log"]
    except (ValueError, KeyError, IndexError, TypeError):
        return []
    return [str(e.get("Output", "")).strip()[:200] for e in log[-count:] if e.get("Output")]


def report(run: Run = docker, lines: int = 5) -> tuple[list[str], int]:
    out = run("compose", "ps", "-a", "--format", "json")
    if out is None:
        return ["docker compose ps failed (docker down or LEVELS_DIR unset)"], 1
    rows = parse_ps(out)
    result: list[str] = []
    bad = 0
    for row in rows:
        name = row.get("Service") or row.get("Name", "?")
        result.append(f"{name} state={row.get('State', '?')} health={row.get('Health') or 'n/a'}")
        if not is_bad(row):
            continue
        bad += 1
        for probe in probe_output(run("inspect", row.get("ID", name))):
            result.append(f"  probe: {probe}")
        logs = (run("compose", "logs", "--no-color", "--tail", str(lines), name) or "").splitlines()
        result.extend(f"  log: {ln[:200]}" for ln in logs[-lines:])
    if not rows:
        result.append("no compose services found")
        bad = 1
    return result, 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lines", type=int, default=5, help="log lines for unhealthy services")
    args = parser.parse_args(argv)
    lines, rc = report(lines=args.lines)
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main())
