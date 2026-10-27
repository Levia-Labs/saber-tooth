"""Commit exactly the named paths: format them, stage them, commit, retry once, verify.

Runs ruff format on .py paths and prettier on md/json/yaml/css/ts/tsx/js paths, stages only
those paths, appends the Co-Authored-By trailer once and never skips hooks. When a hook
modifies files the paths are re-staged and the commit retried once. Never pushes.

Usage: uv run python scripts/commit.py -m "<message>" <paths...>
"""

import argparse
import subprocess  # nosec B404 - fixed argv lists, no shell
import sys
from collections.abc import Callable
from pathlib import Path

TRAILER = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
PRETTIER_EXT = {".md", ".json", ".yaml", ".yml", ".css", ".ts", ".tsx", ".js", ".mjs"}
Runner = Callable[[list[str]], subprocess.CompletedProcess]


def build_message(message: str) -> str:
    body = message.strip()
    return body if TRAILER in body else f"{body}\n\n{TRAILER}"


def split_paths(paths: list[str]) -> tuple[list[str], list[str]]:
    """(python paths, prettier paths) among the existing files in `paths`."""
    existing = [p for p in paths if Path(p).is_file()]
    py = [p for p in existing if Path(p).suffix == ".py"]
    pretty = [p for p in existing if Path(p).suffix in PRETTIER_EXT]
    return py, pretty


def check_paths(paths: list[str]) -> None:
    if not paths:
        raise ValueError("no paths given")
    for p in paths:
        if p.startswith("-") or ".." in Path(p).parts:
            raise ValueError(f"invalid path: {p!r}")


def run(argv: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(  # nosec B603 B607 - constant argv, validated paths, no shell
            argv, capture_output=True, check=False, encoding="utf-8"
        )
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


def format_paths(paths: list[str], runner: Runner = run) -> list[str]:
    py, pretty = split_paths(paths)
    warnings = []
    if py and runner(["uv", "run", "ruff", "format", "--", *py]).returncode:
        warnings.append("ruff format failed")
    if pretty and runner(["npx", "--no-install", "prettier", "--write", "--", *pretty]).returncode:
        warnings.append("prettier unavailable or failed; the pre-commit hook will format")
    return warnings


def commit(message: str, paths: list[str], runner: Runner = run) -> tuple[int, str]:
    """Stage and commit `paths`; returns (rc, hook output of the last attempt)."""
    full = build_message(message)
    res = subprocess.CompletedProcess([], 1, "", "")
    for _ in range(2):
        runner(["git", "add", "--", *paths])
        res = runner(["git", "commit", "-m", full, "--", *paths])
        if res.returncode == 0:
            break
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def verify(message: str, runner: Runner = run) -> str | None:
    """Short hash when HEAD carries the message subject, else None."""
    subject = runner(["git", "log", "-1", "--format=%s"]).stdout.strip()
    if subject != message.strip().splitlines()[0]:
        return None
    return runner(["git", "log", "-1", "--format=%h"]).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-m", "--message", required=True, help="commit message")
    parser.add_argument("paths", nargs="*", help="files to format, stage and commit")
    args = parser.parse_args(argv)
    try:
        check_paths(args.paths)
    except ValueError as exc:
        print(f"commit: {exc}", file=sys.stderr)
        return 2
    for warning in format_paths(args.paths):
        print(f"warn: {warning}")
    rc, output = commit(args.message, args.paths)
    short = verify(args.message) if rc == 0 else None
    if rc or not short:
        print("commit failed:\n" + "\n".join(output.strip().splitlines()[-15:]), file=sys.stderr)
        return rc or 1
    print(f"committed {short} {args.message.strip().splitlines()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
