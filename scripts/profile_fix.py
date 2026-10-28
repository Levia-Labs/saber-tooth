"""Profile the Fix pipeline on a copy of one map folder, in-process and offline.

Usage:
    uv run python scripts/profile_fix.py <map folder> [--rounds N] [--top 25]
        [--analysis <beat-analyser project dir>]

The folder is copied into a temporary levels dir and the source is never written.
Prints phase timings, per-round counts and the top functions by cumulative and own
time; the full pstats file is written next to the printed temp dir path.
Exit 0 ok, 1 failure, 2 usage.
"""

import argparse
import cProfile
import pstats
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saber_tooth.analysis import read_project
from saber_tooth.checks import run_checks
from saber_tooth.lightshow import BUNDLED
from saber_tooth.mapio import load_map
from saber_tooth.service import fix as fixmod
from saber_tooth.service.lightshow_set import active_templates
from saber_tooth.service.util import map_id_for
from saber_tooth.service.writeout import write_fixed


def fmt_func(key: tuple[str, int, str]) -> str:
    """`file:line function` with only the file name."""
    return f"{Path(key[0]).name}:{key[1]} {key[2]}"


def top_rows(stats: dict, sort: str, n: int) -> list[tuple[str, int, float]]:
    """(label, calls, seconds) of the n biggest entries by `cumtime` or `tottime`.

    `stats` is the `pstats.Stats.stats` mapping: key -> (cc, nc, tottime, cumtime, callers).
    """
    idx = 3 if sort == "cumtime" else 2
    rows = sorted(stats.items(), key=lambda kv: kv[1][idx], reverse=True)[:n]
    return [(fmt_func(k), v[1], v[idx]) for k, v in rows]


def table(title: str, rows: list[tuple[str, int, float]]) -> list[str]:
    out = [f"top by {title}: calls  seconds  function"]
    out += [f"  {calls:>7} {secs:8.3f}  {label}" for label, calls, secs in rows]
    return out


def round_lines(rounds: list[dict]) -> list[str]:
    return [
        f"round {i}: findings={r['findings']} tried={r['tried']} applied={r['applied']} "
        f"checks={r['check_s']:.3f}s propose={r['propose_s']:.3f}s apply={r['apply_s']:.3f}s"
        for i, r in enumerate(rounds, 1)
    ]


class Recorder:
    """Wraps the engine's check, propose and apply calls to time them per round."""

    def __init__(self) -> None:
        self.checks: list[tuple[int, float]] = []  # (findings, seconds) per run_checks call
        self.proposals: list[
            tuple[int, bool, float, float]
        ] = []  # (check index, ok, propose, apply)
        self._apply_s = 0.0

    def run_checks(self, *args, **kwargs):
        t = time.perf_counter()
        out = run_checks(*args, **kwargs)
        self.checks.append((len(out), time.perf_counter() - t))
        return out

    def propose(self, *args, **kwargs):
        t = time.perf_counter()
        out = fixmod_propose(*args, **kwargs)
        self.proposals.append(
            [len(self.checks) - 1, out.proposal is not None, time.perf_counter() - t, 0.0]
        )
        return out

    def apply(self, *args, **kwargs):
        t = time.perf_counter()
        out = fixmod_apply(*args, **kwargs)
        self.proposals[-1][3] = time.perf_counter() - t
        return out

    def rounds(self, n_rounds: int) -> tuple[list[dict], float]:
        """Per-round stats for the first `n_rounds` checks, plus seconds of the trailing verify."""
        out = []
        for i, (found, secs) in enumerate(self.checks[:n_rounds]):
            mine = [p for p in self.proposals if p[0] == i]
            out.append(
                {
                    "findings": found,
                    "tried": len(mine),
                    "applied": sum(1 for p in mine if p[1]),
                    "check_s": secs,
                    "propose_s": sum(p[2] for p in mine),
                    "apply_s": sum(p[3] for p in mine),
                }
            )
        verify = sum(s for _, s in self.checks[n_rounds:])
        return out, verify


fixmod_propose = fixmod.propose_with_reason
fixmod_apply = fixmod.apply_ops


def run(source: Path, rounds: int, top: int, analysis_dir: Path | None) -> list[str]:
    if not source.is_dir():
        raise SystemExit(f"not a directory: {source}")
    work = Path(tempfile.mkdtemp(prefix="profile-fix-"))
    levels, data = work / "levels", work / "data"
    levels.mkdir()
    data.mkdir()
    folder = levels / source.name
    shutil.copytree(source, folder)
    lines = [f"temp: {work}"]
    phases: list[tuple[str, float]] = []

    def timed(name, fn):
        t = time.perf_counter()
        out = fn()
        phases.append((name, time.perf_counter() - t))
        return out

    rec = Recorder()
    prof = cProfile.Profile()
    prof.enable()
    try:
        original = timed("load", lambda: load_map(folder))
        analysis = timed(
            "analyse", lambda: read_project(analysis_dir) if analysis_dir is not None else None
        )
        before = timed("initial checks", lambda: run_checks(original, analysis))
        templates = active_templates(data, BUNDLED)
        seed = int(map_id_for(folder.name)[:8], 16)
        fixmod.run_checks, fixmod.propose_with_reason, fixmod.apply_ops = (
            rec.run_checks,
            rec.propose,
            rec.apply,
        )
        try:
            fixed = timed(
                "fix rounds",
                lambda: fixmod.fix_beatmap(original, analysis, templates, seed, rounds),
            )
        finally:
            fixmod.run_checks, fixmod.propose_with_reason, fixmod.apply_ops = (
                run_checks,
                fixmod_propose,
                fixmod_apply,
            )
        after = before
        if fixed.steps:
            fixed.fixed.info.song_name += fixmod.SUFFIX

            def write():
                return write_fixed(levels, folder, fixed.fixed, folder.name + fixmod.SUFFIX)

            target = timed("write", write)
            after = timed("final checks", lambda: run_checks(load_map(target), analysis))
    finally:
        prof.disable()
    per_round, verify = rec.rounds(fixed.rounds)
    lines += [f"phase {name}: {secs:.3f}s" for name, secs in phases]
    lines.append(f"verify inside fix: {verify:.3f}s")
    lines.append(
        f"findings before={len(before)} after={len(after)} rounds={fixed.rounds} "
        f"applied={len(fixed.steps)} unfixed={len(fixed.unfixed)}"
    )
    lines += round_lines(per_round)
    out = work / "profile.pstats"
    prof.dump_stats(str(out))
    stats = pstats.Stats(str(out)).stats  # type: ignore[attr-defined]
    lines += table("cumtime", top_rows(stats, "cumtime", top))
    lines += table("tottime", top_rows(stats, "tottime", top))
    lines.append(f"pstats: {out}")
    return lines


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("folder", type=Path)
    p.add_argument("--rounds", type=int, default=fixmod.MAX_ROUNDS)
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--analysis", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        lines = run(args.folder, args.rounds, args.top, args.analysis)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
