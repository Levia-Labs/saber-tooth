"""One-line repo state for the main worktree and every linked worktree. Read-only.

Per line: branch, ahead/behind origin (or `no upstream`), dirty and untracked counts, the
`.crepidoma` submodule commit and whether it equals the submodule's origin/main.

Usage: uv run python scripts/sync.py [--fetch]
"""

import argparse
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
from collections.abc import Callable

Git = Callable[..., str | None]
SUBMODULE = ".crepidoma"


def git(path: str, *args: str) -> str | None:
    """Run git in `path`; stdout stripped, or None when the command fails."""
    try:
        res = subprocess.run(  # nosec B603 B607 - constant argv, no shell, git from PATH
            ["git", "-C", path, *args], capture_output=True, check=False, encoding="utf-8"
        )
    except OSError:
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def parse_worktrees(porcelain: str) -> list[tuple[str, str]]:
    """(path, branch) per worktree from `git worktree list --porcelain`; branch may be detached."""
    result: list[tuple[str, str]] = []
    path, branch = "", "(detached)"
    for line in [*porcelain.splitlines(), ""]:
        if line.startswith("worktree "):
            path = line[len("worktree ") :]
        elif line.startswith("branch "):
            branch = line[len("branch ") :].removeprefix("refs/heads/")
        elif not line and path:
            result.append((path, branch))
            path, branch = "", "(detached)"
    return result


def parse_status(porcelain: str) -> tuple[int, int]:
    """(dirty, untracked) counts from `git status --porcelain`."""
    lines = [ln for ln in porcelain.splitlines() if ln]
    untracked = sum(1 for ln in lines if ln.startswith("??"))
    return len(lines) - untracked, untracked


def ahead_behind(counts: str | None) -> str:
    """Format `behind<TAB>ahead` output of rev-list --left-right --count @{u}...HEAD."""
    if not counts:
        return "no upstream"
    behind, ahead = counts.split()
    return f"+{ahead}/-{behind}"


def submodule_state(path: str, run: Git = git) -> str:
    sub = f"{path}/{SUBMODULE}"
    head = run(sub, "rev-parse", "--short", "HEAD")
    if not head:
        return f"{SUBMODULE} missing"
    remote = run(sub, "rev-parse", "--short", "origin/main")
    state = "unknown" if not remote else ("match" if remote == head else f"differs({remote})")
    return f"{SUBMODULE} {head} {state}"


def describe(path: str, branch: str, run: Git = git) -> str:
    dirty, untracked = parse_status(run(path, "status", "--porcelain") or "")
    ab = ahead_behind(run(path, "rev-list", "--left-right", "--count", "@{u}...HEAD"))
    return (
        f"{path} [{branch}] {ab} dirty={dirty} untracked={untracked} {submodule_state(path, run)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fetch", action="store_true", help="git fetch before reporting")
    args = parser.parse_args(argv)
    listing = git(".", "worktree", "list", "--porcelain")
    if listing is None:
        print("not a git repository", file=sys.stderr)
        return 1
    trees = parse_worktrees(listing)
    if args.fetch:
        git(".", "fetch", "--quiet")
        for path, _ in trees[:1]:
            git(f"{path}/{SUBMODULE}", "fetch", "--quiet")
    for path, branch in trees:
        print(describe(path, branch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
