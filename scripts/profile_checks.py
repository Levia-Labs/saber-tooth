"""Time the rule engine on a synthetic dense map: per rule, per batch, whole scan.

Usage: uv run python scripts/profile_checks.py [--notes 3400] [--seed 1]
"""

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saber_tooth.checks import RULES, run_checks
from saber_tooth.fixer.window import batch_edges, batch_of, window_findings
from saber_tooth.model import Beatmap, Color, Cut, Difficulty, MapInfo, Note, Wall
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing


def synthetic(count: int, seed: int = 1, name: str = "Expert") -> Beatmap:
    rng = random.Random(seed)  # noqa: S311  deterministic data
    notes = [
        Note(
            8 + i * 0.1, rng.randint(0, 3), rng.randint(0, 2), Color(i % 2), Cut(rng.randint(0, 8))
        )
        for i in range(count)
    ]
    walls = [
        Wall(8 + i * 3.7, rng.randint(0, 3), 0, rng.choice([0.3, 1.5]), rng.randint(1, 2), 3)
        for i in range(count // 30)
    ]
    info = MapInfo("s", "", "a", "m", 120.0, "song.egg", "cover.png", 0, 10, "NiceEnvironment")
    return Beatmap(info, {name: Difficulty(name, 16, 0, notes=sorted(notes), walls=walls)})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", type=int, default=3400)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    m = synthetic(a.notes, a.seed)
    name = "Expert"
    d, profile = m.difficulties[name], PROFILES[name]
    timing = Timing(m.info.bpm, d.bpm_events)
    t = time.perf_counter()
    swings = build_swings(d.notes, timing)
    print(f"build_swings: {time.perf_counter() - t:.3f}s")
    for rid, rule in RULES.items():
        t = time.perf_counter()
        n = len(rule(d, swings, timing, profile, None))
        print(f"rule {rid:14} {time.perf_counter() - t:.3f}s findings={n}")
    t = time.perf_counter()
    found = run_checks(m, None, difficulty=name)
    print(f"whole check: {time.perf_counter() - t:.3f}s findings={len(found)}")
    edges = batch_edges(d)
    t = time.perf_counter()
    for i in range(len(edges) + 1):
        lo = edges[i - 1] if i else 0.0
        hi = edges[i] if i < len(edges) else d.notes[-1].beat
        window_findings(m, name, lo, hi, None)
    print(
        f"window per batch: {(time.perf_counter() - t) / (len(edges) + 1):.3f}s x {len(edges) + 1}"
    )
    print(f"window sum: {time.perf_counter() - t:.3f}s; batch of 8.0={batch_of(edges, 8.0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
