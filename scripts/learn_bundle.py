"""Regenerate the bundled lightshow set from a levels directory, reproducibly.

Learns one-bar vanilla lighting units from every map folder under <levels_dir> and writes
src/saber_tooth/lightshow/data/templates.json.gz (gzip mtime 0, so equal input gives equal bytes).
Prints environments, units and file size.

Usage: uv run python scripts/learn_bundle.py <levels_dir> [--out PATH]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "src" / "saber_tooth" / "lightshow" / "data" / "templates.json.gz"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("levels_dir", help="folder holding one map folder per level")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output .json.gz path")
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT / "src"))
    from saber_tooth.lightshow import learn

    try:
        templates = learn(Path(args.levels_dir))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        templates.save(out)
    except OSError as exc:
        print(f"learn-bundle: {exc}", file=sys.stderr)
        return 1
    units = sum(len(u) for u in templates.units.values())
    print(f"envs={len(templates.units)} units={units} bytes={out.stat().st_size} out={out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
