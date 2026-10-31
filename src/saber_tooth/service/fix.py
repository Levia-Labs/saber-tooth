"""One-click fix: the batch engine of fixrun.py, saved as it goes into a saber-tooth copy."""

import logging
from collections.abc import Callable
from dataclasses import replace

from saber_tooth.checks import Finding, run_checks
from saber_tooth.safe_fs import LevelsWriter
from saber_tooth.service.fixrun import MAX_ROUNDS, FixRun, complete, fix_beatmap
from saber_tooth.service.fixsave import Checkpoint, source_stamp, with_reasons
from saber_tooth.service.util import checkpoint, map_id_for
from saber_tooth.service.writeout import replace_fixed

SUFFIX = " [saber-tooth]"
log = logging.getLogger(__name__)
__all__ = ["MAX_ROUNDS", "SUFFIX", "complete", "counts", "fix_beatmap", "fix_map"]


def counts(findings: list[Finding]) -> dict[str, dict[str, dict[str, int]]]:
    """Findings per difficulty, then severity ("errors", "warnings"), then rule."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for f in findings:
        slot = out.setdefault(f.difficulty, {"errors": {}, "warnings": {}})
        kind = slot["errors" if f.severity == "error" else "warnings"]
        kind[f.rule] = kind.get(f.rule, 0) + 1
    return out


def scan_of(beatmap, analysis, unfixed: list[dict]) -> dict:
    """The copy's own scan, each finding carrying the reason Fix left it unfixed."""
    return scan_dict(run_checks(beatmap, analysis), analysis, unfixed)


def scan_dict(findings: list[Finding], analysis, unfixed: list[dict]) -> dict:
    project = analysis.audio.parent.name if analysis and analysis.audio else None
    found = with_reasons([f.to_dict() for f in findings], unfixed)
    return {"findings": found, "analysis": project}


class _Saver:
    """Writes the working map to the saber-tooth copy and records the checkpoint."""

    def __init__(self, svc, map_id: str, folder, analysis) -> None:
        self.svc, self.map_id, self.folder, self.analysis = svc, map_id, folder, analysis
        self.stamp = source_stamp(folder)
        self.cp = Checkpoint(svc.data, map_id)
        self.name: str | None = None
        self.stored = 0  # steps of this run already in the store
        self.base = 0  # steps applied by earlier, interrupted runs

    def resume(self) -> tuple[FixRun, dict] | None:
        saved = self.cp.load(self.stamp)
        if not saved or not (self.svc.levels / saved["folder"]).is_dir():
            return None
        self.name, self.base = saved["folder"], saved["applied"]
        run = FixRun(
            self.svc._load(self.svc.levels / saved["folder"]),
            unfixed=saved["unfixed"],
            rounds=saved["rounds"],
            completed=saved["completed"],
        )
        return run, saved["position"]

    def __call__(self, run: FixRun, position: dict | None) -> None:
        new = run.steps[self.stored :]
        if new:
            info = run.fixed.info
            if not info.song_name.endswith(SUFFIX):
                info = replace(info, song_name=info.song_name + SUFFIX)
            if self.name is None:
                self.name = LevelsWriter(self.svc.levels).unique_name(self.folder.name + SUFFIX)
            replace_fixed(self.svc.levels, self.folder, replace(run.fixed, info=info), self.name)
            with self.svc._lock:  # short store mutations only
                ids = self.svc.store.add_proposals(self.map_id, [p.to_dict() for p in new])
                self.svc.store.mark_applied(ids)
                scan = scan_of(run.fixed, self.analysis, run.unfixed)
                self.svc.store.replace_open_proposals(map_id_for(self.name), [], scan)
            self.stored = len(run.steps)
        if self.name is None:
            return
        if position is None:
            self.cp.clear()
        else:
            self.cp.save(self.stamp, self.name, run, position, self.base + self.stored)


def fix_map(
    svc,
    map_id: str,
    max_rounds: int = MAX_ROUNDS,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Fix a map into a new folder and report counts before and after, per difficulty and rule.

    The engine works one difficulty and one batch at a time and saves the copy after each
    difficulty pass (and every few batches), so a cancel or failure keeps the finished work
    and a retry resumes from the checkpoint. Every fix is verified against the map as earlier
    fixes left it. The written folder is loaded and checked again for the report.
    """
    folder = svc._folder(map_id)
    original = svc._load(folder)
    checkpoint(progress, "analysing beats")
    analysis = svc._analyse(map_id, original, folder, progress)
    before = run_checks(original, analysis)
    saver = _Saver(svc, map_id, folder, analysis)
    resume = saver.resume()
    if resume:
        checkpoint(progress, f"resuming at {resume[1]['difficulty'] or 'the map'}")

    def on_batch(name: str, i: int, n: int, rnd: int) -> None:
        if progress:
            progress(f"{name}: batch {i} of {n}" + (f" (round {rnd})" if rnd > 1 else ""))

    try:
        run = fix_beatmap(
            original,
            analysis,
            svc._templates(),
            int(map_id[:8], 16),
            max_rounds,
            check=getattr(progress, "check", None),
            on_batch=on_batch,
            on_save=saver,
            resume=resume,
        )
    finally:
        if saver.name:  # the copy of an interrupted run is a real folder: show it
            try:
                svc.refresh_library()
            except Exception:
                log.exception("library refresh failed after fixing %s", map_id)
    checkpoint(progress)  # a cancel during the last attempt is not a success
    report: dict = {
        "map_id": map_id,
        "folder": None,
        "fixed_id": None,
        "analysed": analysis is not None,
        "rounds": run.rounds,
        "applied": saver.base + len(run.steps),
        "before": counts(before),
        "unfixed": run.unfixed,
        "completed": run.completed,
        "resumed": resume is not None,
    }
    if saver.name is None:
        report["after"] = report["before"]
        report["difficulties"] = sorted(original.difficulties)
        return report
    written = svc._load(svc.levels / saver.name)
    after = run_checks(written, analysis)
    fixed_id = map_id_for(saver.name)
    scan = scan_dict(after, analysis, run.unfixed)
    with svc._lock:
        svc.store.replace_open_proposals(fixed_id, [], scan)
    report.update(
        folder=saver.name,
        fixed_id=fixed_id,
        after=counts(after),
        difficulties=sorted(written.difficulties),
        complete=complete(written),
        errors=sum(f.severity == "error" for f in after),
        status=(svc.store.get_map(fixed_id) or {}).get("status"),  # as the library lists the copy
    )
    return report
