"""Measure how much of a map library the offline one-click Fix clears, per rule.

Usage:
    uv run python scripts/fix_rate.py <levels dir> [--sample N] [--rule R] [--seed S]
        [--rounds N] [--jobs J]

A sample of map folders is copied into a temporary levels dir (the source is never written),
the offline autofix runs on each copy, and the findings before and after are summed per rule:
`rule before after fixed% maps_before maps_after`. Maps that fail to load are listed as
parse errors. Exit 0 ok, 1 failure, 2 usage.
"""

import argparse
import random
import shutil
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def pick_sample(folders: list[Path], n: int | None, seed: int = 0) -> list[Path]:
    """Up to n folders, reproducible for a seed and returned in name order."""
    ordered = sorted(folders)
    if n is None or n >= len(ordered):
        return ordered
    rng = random.Random(seed)  # noqa: S311
    return sorted(rng.sample(ordered, max(n, 0)))


def rule_totals(side: dict) -> dict[str, int]:
    """Findings per rule over every difficulty of one `before` or `after` report side."""
    out: dict[str, int] = defaultdict(int)
    for diff in side.values():
        for kind in ("errors", "warnings"):
            for rule, count in diff[kind].items():
                out[rule] += count
    return dict(out)


def aggregate(reports: list[tuple[str, dict]], rule: str | None = None) -> dict[str, dict]:
    """Per rule: findings before and after, and the maps carrying it before and after."""
    rows: dict[str, dict] = {}
    for name, report in reports:
        before, after = rule_totals(report["before"]), rule_totals(report["after"])
        for r in set(before) | set(after):
            if rule is not None and r != rule:
                continue
            row = rows.setdefault(r, {"before": 0, "after": 0, "maps_before": 0, "maps_after": 0})
            row["before"] += before.get(r, 0)
            row["after"] += after.get(r, 0)
            row["maps_before"] += r in before
            if r in after:
                row["maps_after"] += 1
                row.setdefault("failing", []).append(name)
    return rows


def format_table(rows: dict[str, dict], maps: int, parse_errors: list[str]) -> list[str]:
    lines = [f"maps={maps} parse_errors={len(parse_errors)}"]
    lines.append("rule before after fixed% maps_before maps_after")
    for r, v in sorted(rows.items(), key=lambda kv: -kv[1]["after"]):
        pct = 100.0 * (v["before"] - v["after"]) / v["before"] if v["before"] else 100.0
        lines.append(
            f"{r} {v['before']} {v['after']} {pct:.1f} {v['maps_before']} {v['maps_after']}"
        )
    lines += [f"parse-error {name}" for name in parse_errors]
    return lines


def _fix_one(args: tuple[str, str, int]) -> tuple[str, dict | None, str]:
    src, work, rounds = args
    from saber_tooth.autofix import run_autofix

    folder = Path(src)
    try:
        report = run_autofix(
            folder, Path(work) / "levels" / folder.name, Path(work) / "data" / folder.name, rounds
        )
    except Exception as exc:  # one broken map must not abort the run
        return folder.name, None, f"{type(exc).__name__}: {exc}"[:120]
    return folder.name, report, ""


def run(levels: Path, sample: int | None, rule: str | None, seed: int, rounds: int, jobs: int):
    if not levels.is_dir():
        raise SystemExit(f"not a directory: {levels}")
    folders = pick_sample([p for p in levels.iterdir() if p.is_dir()], sample, seed)
    work = Path(tempfile.mkdtemp(prefix="fix-rate-"))
    try:
        todo = [(str(f), str(work), rounds) for f in folders]
        if jobs > 1:
            with ProcessPoolExecutor(jobs) as pool:
                results = list(pool.map(_fix_one, todo))
        else:
            results = [_fix_one(t) for t in todo]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    reports = [(n, r) for n, r, _ in results if r is not None]
    bad = [f"{n} {why}" for n, r, why in results if r is None]
    return format_table(aggregate(reports, rule), len(reports), bad)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("levels", type=Path)
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--rule", default=None)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--rounds", type=int, default=6)
    p.add_argument("--jobs", type=int, default=1)
    args = p.parse_args(argv)
    try:
        lines = run(args.levels, args.sample, args.rule, args.seed, args.rounds, args.jobs)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
