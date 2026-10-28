"""Run the full validation gate; one line per gate and a final PASS or FAIL.

Gates run in a fixed order. Each gate's output goes to `.cache/gate/<name>.log`; a failing
gate prints the log path and the first error-looking line (else the tail), at most 3 lines.

Usage: uv run python scripts/gate.py [--only a,b] [--skip a,b] [--deep] [--list]
"""

import argparse
import re
import shutil
import subprocess  # nosec B404 - argv lists from the constant table below, no shell
import sys
import time
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = Path(".cache") / "gate"
FRONTEND = ["frontend:typecheck", "frontend:lint", "frontend:test", "frontend:build"]
ARGV: dict[str, list[str]] = {
    "pytest": ["uv", "run", "pytest", "-q"],
    "lint:python:check": ["task", "lint:python:check"],
    "lint:precommit": ["task", "lint:precommit"],
    "lint:web:check": ["task", "lint:web:check"],
    **{n: ["npm", "--prefix", "frontend", "run", n.split(":")[1]] for n in FRONTEND},
    "security:sast": ["task", "security:sast"],
    "quality:gate": ["task", "quality:gate"],
    "st:readme-check": ["task", "st:readme-check"],
    "st:compose-check": ["task", "st:compose-check"],
    "quality:deep": ["task", "quality:deep"],
}
STRONG_RE = re.compile(r"^(FAILED|FAIL |ERROR|E {2,})|Traceback|Blocking|error:")
ERROR_RE = re.compile(r"error|fail|traceback", re.IGNORECASE)


def resolve_argv(argv: list[str]) -> list[str]:
    """Replace argv[0] with its full PATH match (npm is npm.cmd on Windows); keep it if absent."""
    return [shutil.which(argv[0]) or argv[0], *argv[1:]]


def select(
    only: list[str], skip: list[str], deep: bool = False, has_frontend: bool = True
) -> list[str]:
    """Ordered gate names after applying --only, --skip, --deep and frontend presence."""
    names = [n for n in ARGV if n != "quality:deep" or deep]
    if not has_frontend:
        names = [n for n in names if n not in FRONTEND]
    if only:
        names = [n for n in names if n in only]
    return [n for n in names if n not in skip]


def excerpt(log: str, count: int = 3) -> list[str]:
    """First error-looking line and what follows it, else the log tail; at most `count` lines."""
    lines = [ln.rstrip() for ln in log.splitlines() if ln.strip()]
    for pattern in (STRONG_RE, ERROR_RE):
        for i, line in enumerate(lines):
            if pattern.search(line.strip()):
                return lines[i : i + count]
    return lines[-count:]


def log_path(name: str, root: Path = LOG_DIR) -> Path:
    return root / (name.replace(":", "-") + ".log")


def run_gate(name: str, log_dir: Path = LOG_DIR, cwd: Path = ROOT) -> tuple[int, float, Path]:
    """Run one gate, capturing combined output to its log. Returns (rc, seconds, log path)."""
    path = cwd / log_path(name, log_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    try:
        with path.open("w", encoding="utf-8") as fh:
            rc = subprocess.run(  # nosec B603 - constant argv table, no shell
                resolve_argv(ARGV[name]), cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, check=False
            ).returncode
    except OSError as exc:
        path.write_text(f"error: cannot start {ARGV[name][0]}: {exc}\n", encoding="utf-8")
        rc = 127
    return rc, time.monotonic() - start, path


def summary(failed: int) -> str:
    return f"gate: PASS ({failed} failed)" if not failed else f"gate: FAIL ({failed} failed)"


def run_all(
    names: list[str],
    runner: Callable[[str], tuple[int, float, Path]] = run_gate,
    out: Callable[[str], None] = print,
) -> int:
    failed = 0
    for name in names:
        rc, secs, path = runner(name)
        out(f"{name} rc={rc} ({secs:.0f}s)")
        if rc:
            failed += 1
            out(f"  log: {path}")
            text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
            for line in excerpt(text):
                out(f"  {line[:200]}")
    out(summary(failed))
    return 1 if failed else 0


def _csv(value: str) -> list[str]:
    return [v for v in value.split(",") if v]


def main(argv: list[str] | None = None) -> int:
    # Gate logs quote tool output (vitest prints check marks); a cp1250 console crashed on them.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", type=_csv, default=[], help="comma list of gates to run")
    parser.add_argument("--skip", type=_csv, default=[], help="comma list of gates to skip")
    parser.add_argument("--deep", action="store_true", help="also run quality:deep")
    parser.add_argument("--list", action="store_true", help="print gate names and exit")
    args = parser.parse_args(argv)
    names = select(args.only, args.skip, args.deep, (ROOT / "frontend").is_dir())
    if args.list:
        print("\n".join(names))
        return 0
    unknown = [n for n in args.only + args.skip if n not in ARGV]
    if unknown:
        print(f"unknown gate: {', '.join(unknown)}", file=sys.stderr)
        return 2
    return run_all(names)


if __name__ == "__main__":
    sys.exit(main())
