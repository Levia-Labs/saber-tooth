"""Write `git diff <range>` to a review file, excluding lockfiles by default.

Prints the file path, byte size, files changed and commit count.

Usage: uv run python scripts/review_diff.py <range> [--out DIR] [--exclude GLOB ...]
"""

import argparse
import re
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
from pathlib import Path

DEFAULT_EXCLUDES = ("package-lock.json", "frontend/package-lock.json", "uv.lock")
RANGE_RE = re.compile(r"^[\w./~^@{}-]+(\.\.\.?[\w./~^@{}-]+)?$")


def validate_range(rng: str) -> str:
    """Reject anything that is not a plain revision or `a..b` range (no options, no spaces)."""
    if rng.startswith("-") or not RANGE_RE.match(rng):
        raise ValueError(f"invalid range: {rng!r}")
    return rng


def out_name(rng: str) -> str:
    """File name `review-<from>..<to>.diff` with path separators made safe."""
    safe = re.sub(r"[^\w.~^@-]", "_", rng.replace("...", ".."))
    if ".." not in safe:
        safe = f"{safe}..HEAD"
    return f"review-{safe}.diff"


def pathspecs(excludes: list[str]) -> list[str]:
    return [".", *(f":(exclude,glob){e}" if "*" in e else f":(exclude){e}" for e in excludes)]


def _git(*args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - git from PATH, validated range, no shell
        ["git", *args], capture_output=True, check=True
    ).stdout.decode("utf-8", errors="replace")


def commit_count(rng: str) -> int:
    spec = rng if ".." in rng else f"{rng}..HEAD"
    return int(_git("rev-list", "--count", spec.replace("...", "..")).strip() or 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("range", help="git revision range, e.g. main..HEAD")
    parser.add_argument("--out", default=".cache/reviews", help="output directory")
    parser.add_argument("--exclude", action="append", default=None, help="extra path or glob")
    args = parser.parse_args(argv)
    try:
        rng = validate_range(args.range)
        specs = pathspecs(list(DEFAULT_EXCLUDES) + (args.exclude or []))
        diff = subprocess.run(  # nosec B603 B607 - validated range, no shell
            ["git", "diff", rng, "--", *specs], capture_output=True, check=True
        ).stdout
        files = [ln for ln in _git("diff", "--name-only", rng, "--", *specs).splitlines() if ln]
        count = commit_count(rng)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"review-diff failed: {exc}", file=sys.stderr)
        return 1
    target = Path(args.out) / out_name(rng)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(diff)
    print(f"{target}\nbytes={len(diff)} files={len(files)} commits={count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
