"""Check that every tracked project folder has a README.md.

Commands:
    readme_check.py            print missing folders (max 20) and `missing=N`; exit 1 if N > 0
    readme_check.py --list     print every folder that requires a README

Usage: uv run python scripts/readme_check.py [--list] [--top N]
"""

import argparse
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

# Any path component in this set removes the folder (and everything below it).
EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".crepidoma",
        "node_modules",
        ".venv",
        "__pycache__",
        ".superpowers",
        ".ratchet",
        ".worktrees",
    }
)

# Fixture roots whose child folders are excluded: a README inside a map or analyser
# fixture folder would alter the test data. The roots themselves still need READMEs.
FIXTURE_ROOTS = ("tests/fixtures/maps", "tests/fixtures/analyser")


def _excluded(folder: str) -> bool:
    if EXCLUDED_PARTS.intersection(PurePosixPath(folder).parts):
        return True
    return any(folder.startswith(root + "/") for root in FIXTURE_ROOTS)


def required_folders(tracked: Iterable[str]) -> list[str]:
    """Sorted folders (root as ".") that are ancestors of tracked files and not excluded."""
    folders = {"."}
    for path in tracked:
        for parent in PurePosixPath(path).parents:
            folders.add(parent.as_posix())
    return sorted(f for f in folders if not _excluded(f))


def missing_folders(tracked: Iterable[str], has_readme: Callable[[str], bool]) -> list[str]:
    return [f for f in required_folders(tracked) if not has_readme(f)]


def format_report(missing: list[str], cap: int = 20) -> list[str]:
    lines = list(missing[:cap])
    if len(missing) > cap:
        lines.append(f"... {len(missing) - cap} more")
    lines.append(f"missing={len(missing)}")
    return lines


def _git_files() -> list[str]:
    out = subprocess.run(  # nosec B603 B607 - constant argv, no shell, git from PATH
        ["git", "ls-files", "-z"], capture_output=True, check=True, encoding="utf-8"
    ).stdout
    return [p for p in out.split("\0") if p]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="print folders requiring a README")
    parser.add_argument("--top", type=int, default=20, help="max missing folders printed")
    args = parser.parse_args(argv)
    try:
        tracked = _git_files()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"git ls-files failed: {exc}", file=sys.stderr)
        return 1
    if args.list:
        print("\n".join(required_folders(tracked)))
        return 0
    missing = missing_folders(tracked, lambda d: (Path(d) / "README.md").is_file())
    print("\n".join(format_report(missing, args.top)))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
