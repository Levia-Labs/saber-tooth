"""Bring a worktree's uncommitted changes into the main checkout's working tree.

Untracked files in the worktree are marked intent-to-add, `git diff --binary` is
exported to a temp file, checked with `git apply --check` against the repo root,
then applied unless --check. Never commits or resets.

Usage: uv run python scripts/lane_apply.py <worktree> [--paths p1 p2 ...] [--check]
Exit: 0 ok, 1 failure, 2 usage.
"""

import argparse
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
import tempfile
from pathlib import Path

MAX_FAIL_LINES = 20


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True)  # nosec B603 B607


def parse_name_status(raw: bytes) -> list[str]:
    """Turn `diff --name-status -z` output into `A path` receipt lines."""
    parts = raw.decode("utf-8").split("\0")
    out: list[str] = []
    i = 0
    while i + 1 < len(parts):
        status = parts[i][:1]
        if status in ("R", "C"):
            out.append(f"D {parts[i + 1]}")
            out.append(f"A {parts[i + 2]}")
            i += 3
        else:
            out.append(f"{status} {parts[i + 1]}")
            i += 2
    return out


def failure_lines(stderr: bytes) -> list[str]:
    text = stderr.decode("utf-8", "replace")
    return [ln for ln in text.splitlines() if ln.strip()][:MAX_FAIL_LINES]


def run(
    worktree: Path, paths: list[str], check_only: bool, root: Path | None = None
) -> tuple[int, list[str]]:
    if root is None:
        top = subprocess.run(  # nosec B603 B607
            ["git", "rev-parse", "--show-toplevel"], capture_output=True
        )
        if top.returncode:
            return 1, ["not inside a git repository"]
        root = Path(top.stdout.decode("utf-8").strip())
    if not worktree.is_dir():
        return 1, [f"no such worktree: {worktree}"]
    spec = ["--", *paths] if paths else []
    untracked = _git(worktree, "ls-files", "-z", "--others", "--exclude-standard", *spec)
    names = [n for n in untracked.stdout.decode("utf-8").split("\0") if n]
    if names:
        added = _git(worktree, "add", "-N", "--", *names)
        if added.returncode:
            return 1, failure_lines(added.stderr)
    diff = _git(worktree, "diff", "--binary", *spec)
    if diff.returncode:
        return 1, failure_lines(diff.stderr)
    lines = parse_name_status(_git(worktree, "diff", "--name-status", "-z", *spec).stdout)
    if lines:
        with tempfile.TemporaryDirectory() as tmp:
            patch = Path(tmp) / "lane.patch"
            patch.write_bytes(diff.stdout)
            for flags in [["--check"]] if check_only else [["--check"], []]:
                done = _git(root, "apply", *flags, str(patch))
                if done.returncode:
                    return 1, failure_lines(done.stderr)
    return 0, [*lines, f"applied {len(lines)} files"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("worktree", type=Path)
    parser.add_argument("--paths", nargs="+", default=[])
    parser.add_argument("--check", action="store_true", help="verify only, change nothing")
    args = parser.parse_args(argv)
    code, lines = run(args.worktree, args.paths, args.check)
    print("\n".join(lines), file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
