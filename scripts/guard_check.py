"""Read-only: run the map-folder deletion guard over a levels dir and count pass/refuse per reason.

Usage: uv run python scripts/guard_check.py <levels_dir> [--list]
Exit: 0 ok, 2 usage. Nothing is ever deleted.
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from saber_tooth.map_folder_guard import check_map_folder


def reason_key(reason: str) -> str:
    """Strip file names and counts so reasons group by rule."""
    return re.sub(r":.*$", "", reason)


def survey(levels: Path) -> tuple[int, int, Counter[str], list[tuple[str, list[str]]]]:
    passed = refused = 0
    counts: Counter[str] = Counter()
    refusals: list[tuple[str, list[str]]] = []
    for folder in sorted(p for p in levels.iterdir() if p.is_dir() or p.is_symlink()):
        reasons = check_map_folder(folder, levels)
        if not reasons:
            passed += 1
            continue
        refused += 1
        refusals.append((folder.name, reasons))
        counts.update({reason_key(r) for r in reasons})
    return passed, refused, counts, refusals


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("levels", type=Path)
    ap.add_argument("--list", action="store_true", help="print each refused folder and reasons")
    args = ap.parse_args(argv)
    if not args.levels.is_dir():
        print(f"FAIL not a directory: {args.levels}")
        return 2
    passed, refused, counts, refusals = survey(args.levels)
    print(f"pass={passed} refuse={refused}")
    for reason, n in counts.most_common():
        print(f"{n:6d}  {reason}")
    if args.list:
        for name, reasons in refusals:
            print(f"{name}: {'; '.join(reasons)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
