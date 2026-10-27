"""Apply approved proposals in id order to an evolving map, superseding stale ones."""

from dataclasses import dataclass, field

from saber_tooth.analysis import Analysis
from saber_tooth.checks import Finding, run_checks
from saber_tooth.fixer import OpConflict, apply_ops, find_same, op_from_dict, propose
from saber_tooth.lightshow import Templates
from saber_tooth.model import Beatmap
from saber_tooth.service.errors import ApplyConflict
from saber_tooth.service.util import finding_from_dict, overlaps, related, span
from saber_tooth.store import Store


@dataclass
class Outcome:
    applied: list[int] = field(default_factory=list)
    superseded: list[int] = field(default_factory=list)
    needs_review: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "applied": self.applied,
            "superseded": self.superseded,
            "needs_review": self.needs_review,
        }


def _finding_of(p: dict, known: list[dict], spans: list) -> Finding | None:
    """The finding a proposal fixes: stored with it, else the scan finding its ops fall in."""
    if p.get("finding"):
        return finding_from_dict(p["finding"])
    for d in known:
        if d["rule"] != p["rule"] or d["difficulty"] != p["difficulty"]:
            continue
        mine = (d["difficulty"], float(d["beat_start"]), float(d["beat_end"]))
        if any(overlaps(mine, s) for s in spans):
            return finding_from_dict(d)
    return None


def apply_in_order(
    store: Store,
    map_id: str,
    original: Beatmap,
    approved: list[dict],
    analysis: Analysis | None,
    templates: Templates | None,
    seed: int,
) -> tuple[Beatmap, list[dict], Outcome]:
    """Fold the approved proposals into the map; return it, the ones applied and the outcome.

    A proposal whose ops no longer fit because an earlier one changed the map is re-checked:
    superseded when its finding is gone, else replaced by a fresh pending proposal.
    """
    cur, kept, out = original, [], Outcome()
    for n, p in enumerate(approved):
        try:
            ops = [op_from_dict(o) for o in p["ops"]]
            cur = apply_ops(cur, ops)
            kept.append(p)
            out.applied.append(p["id"])
            continue
        except OpConflict as exc:
            conflict = exc
        except (KeyError, ValueError, TypeError) as exc:
            raise ApplyConflict(f"proposal is unreadable: {exc}", [p["id"]]) from exc
        spans = [s for s in map(span, ops) if s]
        info = store.scan_info(map_id)
        target = _finding_of(p, info["findings"] if info else [], spans)
        fail = ApplyConflict(
            f"proposals conflict: {conflict}", related(spans, approved[: n + 1]) or [p["id"]]
        )
        if target is None:
            raise fail from conflict
        now = find_same(run_checks(cur, analysis), target)
        if now is None:
            store.supersede(p["id"])
            out.superseded.append(p["id"])
            continue
        fresh = propose(cur, now, analysis, templates, seed)
        if fresh is None:
            raise fail from conflict
        new_id = store.supersede(p["id"], {**fresh.to_dict(), "finding": now.to_dict()})
        out.superseded.append(p["id"])
        if new_id is not None:
            out.needs_review.append(new_id)
    return cur, kept, out
