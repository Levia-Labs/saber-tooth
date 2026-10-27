"""Bump the `.crepidoma` submodule: fetch, check out a ref, log, verify, stage the gitlink.

Prints the old..new commit log, runs the gate subset lint:precommit, lint:web:check and
quality:gate, and stages the gitlink only when that passes. Never commits.

Usage: uv run python scripts/crepidoma_bump.py [<ref>]
"""

import argparse
import re
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
from pathlib import Path

SUB = ".crepidoma"
GATES = "lint:precommit,lint:web:check,quality:gate"
REF_RE = re.compile(r"^\w[\w./-]*$")


def git(*args: str, cwd: str = ".") -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - constant argv, validated ref, no shell
        ["git", *args], cwd=cwd, capture_output=True, check=False, encoding="utf-8"
    )


def log_lines(old: str, new: str) -> list[str]:
    if old == new:
        return ["no change"]
    found = git("log", "--oneline", f"{old}..{new}", cwd=SUB).stdout.strip().splitlines()
    return found or [f"{old[:7]}..{new[:7]} (no linear history)"]


def bump(ref: str) -> int:
    if not REF_RE.match(ref):
        print(f"invalid ref: {ref!r}", file=sys.stderr)
        return 2
    if not Path(SUB, ".git").exists():
        print(f"{SUB} is not initialised: git submodule update --init", file=sys.stderr)
        return 1
    old = git("rev-parse", "HEAD", cwd=SUB).stdout.strip()
    for step in (["fetch", "--quiet", "origin"], ["checkout", "--quiet", ref]):
        res = git(*step, cwd=SUB)
        if res.returncode:
            print(f"git {step[0]} failed: {res.stderr.strip()[:300]}", file=sys.stderr)
            return 1
    new = git("rev-parse", "HEAD", cwd=SUB).stdout.strip()
    print("\n".join(log_lines(old, new)))
    gate = Path(__file__).with_name("gate.py")
    rc = subprocess.run(  # nosec B603 - constant argv, no shell
        [sys.executable, str(gate), "--only", GATES], check=False
    ).returncode
    if rc:
        print("gate failed; gitlink not staged", file=sys.stderr)
        return rc
    git("add", "--", SUB)
    print(f"staged {SUB} {old[:7]}..{new[:7]}; commit it yourself")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ref", nargs="?", default="origin/main", help="ref (default origin/main)")
    return bump(parser.parse_args(argv).ref)


if __name__ == "__main__":
    sys.exit(main())
