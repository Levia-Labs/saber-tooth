"""Parallel work lanes as git worktrees under `.worktrees/<name>` on branch `lane/<name>`.

Commands:
    lane.py new <name> [--base main]   create the worktree, init the submodule, npm ci
    lane.py list                       lanes with ahead/behind main and dirty counts
    lane.py done <name>                remove a clean, fully merged lane (needs CONFIRM=yes)

Usage: uv run python scripts/lane.py new|list|done ...
"""

import argparse
import os
import re
import shutil
import subprocess  # nosec B404 - fixed git/npm argv, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync import parse_status, parse_worktrees

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
BASE_RE = re.compile(r"^[\w][\w./-]*$")


class LaneError(Exception):
    """A refused or failed lane operation."""


def valid_name(name: str) -> str:
    if not NAME_RE.match(name):
        raise LaneError(f"invalid lane name {name!r}: use lowercase letters, digits, hyphens")
    return name


def git(*args: str, cwd: str | Path = ".", check: bool = True) -> str:
    try:
        res = subprocess.run(  # nosec B603 B607 - constant argv, validated names, no shell
            ["git", *args], cwd=cwd, capture_output=True, check=False, encoding="utf-8"
        )
    except OSError as exc:
        raise LaneError(f"git unavailable: {exc}") from exc
    if check and res.returncode:
        raise LaneError(f"git {args[0]} failed: {(res.stderr or res.stdout).strip()[:300]}")
    return res.stdout.strip() if res.returncode == 0 else ""


def main_tree() -> Path:
    return Path(parse_worktrees(git("worktree", "list", "--porcelain"))[0][0])


def lane_path(root: Path, name: str) -> Path:
    return root / ".worktrees" / valid_name(name)


def ensure_excluded(root: Path) -> None:
    exclude = Path(git("rev-parse", "--git-path", "info/exclude", cwd=root))
    exclude = exclude if exclude.is_absolute() else root / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    current = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    if ".worktrees/" not in current.splitlines():
        with exclude.open("a", encoding="utf-8") as fh:
            fh.write(("" if current.endswith("\n") or not current else "\n") + ".worktrees/\n")


def create(name: str, base: str, root: Path) -> list[str]:
    if not BASE_RE.match(base):
        raise LaneError(f"invalid base {base!r}")
    path = lane_path(root, name)
    if path.exists():
        raise LaneError(f"{path} already exists")
    ensure_excluded(root)
    git("worktree", "add", "-b", f"lane/{name}", str(path), base, cwd=root)
    git("submodule", "update", "--init", cwd=path)
    lines = [f"lane {name}: {path} on lane/{name} from {base}"]
    npm = shutil.which("npm")
    if (path / "frontend" / "package.json").is_file() and npm:
        res = subprocess.run(  # nosec B603 - constant argv, no shell
            [npm, "ci"], cwd=path / "frontend", capture_output=True, check=False
        )
        lines.append(f"npm ci rc={res.returncode}")
    return lines


def check_removable(name: str, root: Path) -> Path:
    path = lane_path(root, name)
    if not path.is_dir():
        raise LaneError(f"no lane at {path}")
    dirty, untracked = parse_status(git("status", "--porcelain", cwd=path))
    if dirty or untracked:
        raise LaneError(f"lane {name} not clean: dirty={dirty} untracked={untracked}")
    ancestor = subprocess.run(  # nosec B603 B607 - constant argv, validated name, no shell
        ["git", "merge-base", "--is-ancestor", f"lane/{name}", "main"], cwd=root, check=False
    )
    if ancestor.returncode:
        raise LaneError(f"lane/{name} has commits not merged into main")
    return path


def remove(name: str, root: Path, env: dict[str, str] | None = None) -> str:
    if (env if env is not None else os.environ).get("CONFIRM") != "yes":
        raise LaneError("destructive: set CONFIRM=yes to remove a lane")
    path = check_removable(name, root)
    git("worktree", "remove", "--force", str(path), cwd=root)
    git("branch", "-d", f"lane/{name}", cwd=root)
    return f"lane {name} removed"


def list_lanes() -> list[str]:
    lines = []
    for path, branch in parse_worktrees(git("worktree", "list", "--porcelain")):
        if not branch.startswith("lane/"):
            continue
        counts = git("rev-list", "--left-right", "--count", f"main...{branch}", cwd=path)
        behind, ahead = counts.split() if counts else ("?", "?")
        dirty, untracked = parse_status(git("status", "--porcelain", cwd=path, check=False))
        lines.append(f"{branch} +{ahead}/-{behind} dirty={dirty} untracked={untracked} {path}")
    return lines or ["no lanes"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    new = sub.add_parser("new", help="create a lane")
    new.add_argument("name")
    new.add_argument("--base", default="main")
    done = sub.add_parser("done", help="remove a merged, clean lane (CONFIRM=yes)")
    done.add_argument("name")
    sub.add_parser("list", help="list lanes")
    args = parser.parse_args(argv)
    try:
        root = main_tree()
        if args.cmd == "new":
            out = create(args.name, args.base, root)
        elif args.cmd == "done":
            out = [remove(args.name, root)]
        else:
            out = list_lanes()
    except LaneError as exc:
        print(f"lane: {exc}", file=sys.stderr)
        return 1
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
