"""Library-wide finding counts per rule and severity, from each map's latest scan."""

import json
from pathlib import Path

from saber_tooth.copynames import is_fixed_copy, strip_fixed
from saber_tooth.generated import generated_ids

_CAP = 50
_ROWS_SQL = (
    "SELECT m.id, m.folder, m.parse_error, s.keys_json FROM maps m"
    " LEFT JOIN scans s ON s.map_id = m.id ORDER BY m.folder, m.id"
)


def _visible(store) -> list[dict]:
    """The chain rule, in one place: every map except an original whose fixed copy exists
    (it is left to the copy)."""
    rows = [dict(r) for r in store._query(_ROWS_SQL)]
    copied = {strip_fixed(r["folder"]) for r in rows if is_fixed_copy(r["folder"])}
    return [r for r in rows if is_fixed_copy(r["folder"]) or strip_fixed(r["folder"]) not in copied]


def _chains_with_findings(store) -> list[dict]:
    """Readable visible maps whose latest scan has findings, one per chain."""
    out, chains = [], set()
    for r in _visible(store):
        keys = json.loads(r["keys_json"]) if r["keys_json"] else []
        key = strip_fixed(r["folder"])
        if r["parse_error"] or not keys or key in chains:
            continue
        chains.add(key)
        out.append({**r, "keys": keys})
    return out


def findings_summary(store, levels: Path) -> dict:
    """Findings per rule and severity over visible maps; hidden originals are excluded.

    maps.total counts visible maps (copies and originals without a copy), matching the
    library list, not originals hidden behind their fixed copy."""
    visible = _visible(store)
    chains = _chains_with_findings(store)
    tally: dict[tuple, list] = {}
    per_map = []
    for r in chains:
        rules: dict[str, int] = {}
        for k in r["keys"]:
            t = tally.setdefault((k.get("rule"), k.get("severity")), [0, set()])
            t[0] += 1
            t[1].add(r["id"])
            rules[k.get("rule")] = rules.get(k.get("rule"), 0) + 1
        per_map.append({"id": r["id"], "folder": r["folder"], "rules": rules})
    rules_out = sorted(
        (
            {"rule": rule, "severity": sev, "findings": n, "maps": len(ids)}
            for (rule, sev), (n, ids) in tally.items()
        ),
        key=lambda r: (-r["findings"], r["rule"] or "", r["severity"] or ""),
    )
    by_severity: dict[str, int] = {}
    for r in rules_out:
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + r["findings"]
    return {
        "rules": rules_out,
        "severities": by_severity,
        "findings": sum(by_severity.values()),
        "maps": {
            "total": len(visible),
            "scanned": sum(1 for r in visible if r["keys_json"] is not None),
            "with_findings": len(chains),
            "generated": len(generated_ids(store, levels)),
        },
        "maps_with_findings": per_map[:_CAP],
    }


def maps_with_findings(store) -> list[str]:
    """Ids of readable maps whose latest scan has at least one finding, one per chain: an
    original whose fixed copy exists is left to the copy (fixed in place, or clean)."""
    return sorted(r["id"] for r in _chains_with_findings(store))
