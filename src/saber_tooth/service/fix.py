"""One-click fix engine: verified fixes folded one at a time into an evolving map."""

import logging
from dataclasses import dataclass, field

from saber_tooth.analysis import Analysis
from saber_tooth.checks import Finding, run_checks
from saber_tooth.fixer import Proposal, apply_ops, propose_with_reason
from saber_tooth.lightshow import Templates
from saber_tooth.model import DIFFICULTIES, Beatmap
from saber_tooth.service.util import map_id_for
from saber_tooth.service.writeout import write_fixed

MAX_ROUNDS = 6
SUFFIX = " [saber-tooth]"
log = logging.getLogger(__name__)


@dataclass
class FixRun:
    """What the engine did: the fixed map, the proposals folded in and what stayed open."""

    fixed: Beatmap
    steps: list[Proposal] = field(default_factory=list)
    unfixed: list[dict] = field(default_factory=list)
    rounds: int = 0


def counts(findings: list[Finding]) -> dict[str, dict[str, dict[str, int]]]:
    """Findings per difficulty, then severity ("errors", "warnings"), then rule."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for f in findings:
        slot = out.setdefault(f.difficulty, {"errors": {}, "warnings": {}})
        kind = slot["errors" if f.severity == "error" else "warnings"]
        kind[f.rule] = kind.get(f.rule, 0) + 1
    return out


def _order(f: Finding) -> tuple:
    return (f.rule != "missing-difficulty", f.severity != "error", f.difficulty, f.beat_start)


def complete(bm: Beatmap) -> bool:
    return all(name in bm.difficulties for name in DIFFICULTIES)


def fix_beatmap(
    original: Beatmap,
    analysis: Analysis | None,
    templates: Templates | None,
    seed: int,
    max_rounds: int = MAX_ROUNDS,
) -> FixRun:
    """Fix findings one by one, each verified against the map as the earlier fixes left it.

    A proposal is built from the current map, so fixes never overlap-conflict. A round
    ends when every finding was tried; rounds repeat while the previous one changed the map.
    """
    run = FixRun(original)
    cur = original
    for n in range(1, max_rounds + 1):
        run.rounds = n
        findings = sorted(run_checks(cur, analysis), key=_order)
        run.unfixed = []
        progressed = False
        for f in findings:
            out = propose_with_reason(cur, f, analysis, templates, seed)
            if out.proposal is None:
                run.unfixed.append({"finding": f, "reason": out.reason})
                continue
            cur = apply_ops(cur, out.proposal.ops)
            run.steps.append(out.proposal)
            progressed = True
        run.fixed = cur
        if not progressed:
            break
    if run.steps:
        # findings tried before a later fix may have vanished: report only what remains
        now = run_checks(cur, analysis)
        run.unfixed = [u for u in run.unfixed if any(_same(u["finding"], f) for f in now)]
    return run


def _same(a: Finding, b: Finding) -> bool:
    return (a.rule, a.difficulty, a.severity) == (b.rule, b.difficulty, b.severity) and (
        a.beat_start <= b.beat_end and b.beat_start <= a.beat_end
    )


def fix_map(svc, map_id: str, max_rounds: int = MAX_ROUNDS) -> dict:
    """Fix a map into a new folder and report counts before and after, per difficulty and rule.

    Every fix is verified against the map as earlier fixes left it, so overlapping fixes
    cannot conflict. The written folder is loaded and checked again for the report.
    """
    folder = svc._folder(map_id)
    original = svc._load(folder)
    analysis = svc._analyse(map_id, original, folder)
    before = run_checks(original, analysis)
    run = fix_beatmap(original, analysis, svc._templates(), int(map_id[:8], 16), max_rounds)
    report: dict = {
        "map_id": map_id,
        "folder": None,
        "fixed_id": None,
        "analysed": analysis is not None,
        "rounds": run.rounds,
        "applied": len(run.steps),
        "before": counts(before),
        "unfixed": [{**u["finding"].to_dict(), "reason": u["reason"]} for u in run.unfixed],
    }
    if not run.steps:
        report["after"] = report["before"]
        report["difficulties"] = sorted(original.difficulties)
        return report
    run.fixed.info.song_name += SUFFIX
    with svc._lock:
        target = write_fixed(svc.levels, folder, run.fixed, folder.name + SUFFIX)
        ids = svc.store.add_proposals(map_id, [p.to_dict() for p in run.steps])
        svc.store.mark_applied(ids)
        try:
            svc.refresh_library()
        except Exception:
            log.exception("library refresh failed after fixing %s", map_id)
    written = svc._load(target)
    after = run_checks(written, analysis)
    fixed_id = map_id_for(target.name)
    project = analysis.audio.parent.name if analysis and analysis.audio else None
    scan = {"findings": [f.to_dict() for f in after], "analysis": project}
    with svc._lock:
        svc.store.replace_open_proposals(fixed_id, [], scan)
    report.update(
        folder=target.name,
        fixed_id=fixed_id,
        after=counts(after),
        difficulties=sorted(written.difficulties),
        complete=complete(written),
        errors=sum(f.severity == "error" for f in after),
    )
    return report
