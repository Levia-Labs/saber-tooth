"""Scan: one difficulty at a time, one time batch at a time, storing each batch as it is done.

The findings of each batch come from a check of that batch's window (cost follows the batch,
not the difficulty); what costs time is proposing a verified fix for each. Those are proposed
batch by batch,
each fix judged against its own window (fixer.window), and each batch is written to the
store before the next starts, so the first findings show within seconds and a cancel,
timeout or failure keeps every finished batch.
"""

import time

from saber_tooth.checks import MAP_RULES, run_checks
from saber_tooth.fixer import propose
from saber_tooth.fixer.window import batch_edges, batch_of
from saber_tooth.service.util import checkpoint

PROPOSE_BUDGET_S = 600.0  # safety net: after this the rest is stored as findings only


def _batches(svc, bm, analysis):
    """(label, findings) per unit of work: the map-level rules, then each batch of each level."""
    yield "map", run_checks(bm, analysis, rules=set(MAP_RULES))
    for name in sorted(bm.difficulties):
        edges = batch_edges(bm.difficulties[name])
        bounds = [float("-inf"), *edges, float("inf")]
        for i in range(len(edges) + 1):
            found = run_checks(bm, analysis, difficulty=name, window=(bounds[i], bounds[i + 1]))
            group = [f for f in found if batch_of(edges, f.beat_start) == i]
            yield f"{name}: batch {i + 1} of {len(edges) + 1}", group


def scan_map(svc, map_id: str, progress=None) -> tuple[int, bool, int, list[dict]]:
    """Scan and store; (proposals, analysed, findings left unproposed, completed difficulties)."""
    checkpoint(progress, "decoding audio")
    folder = svc._folder(map_id)
    bm = svc._load(folder)
    checkpoint(progress, "analysing beats")
    analysis = svc._analyse(map_id, bm, folder, progress)  # slow: the lock is not held
    checkpoint(progress, "checking rules")
    templates, seed = svc._templates(), int(map_id[:8], 16)
    project = analysis.audio.parent.name if analysis and analysis.audio else None
    deadline = time.monotonic() + PROPOSE_BUDGET_S
    total = skipped = 0
    first, done = True, {}
    for label, findings in _batches(svc, bm, analysis):
        checkpoint(progress, label if label != "map" else None)
        proposals = []
        for f in sorted(findings, key=lambda f: f.severity != "error"):  # errors first
            checkpoint(progress)
            if time.monotonic() > deadline:
                skipped += 1
                continue
            p = propose(bm, f, analysis, templates, seed)
            if p is not None:
                proposals.append({**p.to_dict(), "finding": f.to_dict()})
        dicts = [f.to_dict() for f in findings]
        with svc._lock:
            if first:  # the old results are replaced only once there is something to replace them
                svc.store.replace_open_proposals(
                    map_id, proposals, {"findings": dicts, "analysis": project}
                )
            else:
                svc.store.add_scan_batch(map_id, proposals, dicts)
        first = False
        total += len(proposals)
        if label != "map":
            name = label.split(":")[0]
            done[name] = done.get(name, 0) + 1
    if skipped:
        checkpoint(progress, f"time budget reached: {skipped} findings left unproposed")
    return (
        total,
        analysis is not None,
        skipped,
        [{"difficulty": k, "batches": v} for k, v in done.items()],
    )
