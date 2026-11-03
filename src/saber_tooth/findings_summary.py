"""Library-wide finding counts per rule and severity, from each map's latest scan."""

_RULES_SQL = (
    "SELECT json_extract(f.value, '$.rule') AS rule,"
    " json_extract(f.value, '$.severity') AS severity,"
    " count(*) AS findings, count(DISTINCT s.map_id) AS maps"
    " FROM scans s JOIN maps m ON m.id = s.map_id, json_each(s.keys_json) f"
    " GROUP BY rule, severity ORDER BY findings DESC, rule, severity"
)
_MAPS_SQL = (
    "SELECT count(*) AS total,"
    " coalesce(sum(s.map_id IS NOT NULL), 0) AS scanned,"
    " coalesce(sum(s.map_id IS NOT NULL AND json_array_length(s.keys_json) > 0), 0)"
    " AS with_findings,"
    " coalesce(sum(m.source IS NOT NULL AND m.source != ''), 0) AS generated"
    " FROM maps m LEFT JOIN scans s ON s.map_id = m.id"
)


def findings_summary(store) -> dict:
    """Findings counted per rule and severity, with the number of maps each touches."""
    rules = [dict(r) for r in store._query(_RULES_SQL)]
    row = dict(store._query(_MAPS_SQL)[0])
    by_severity: dict[str, int] = {}
    for r in rules:
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + r["findings"]
    return {
        "rules": rules,
        "severities": by_severity,
        "findings": sum(by_severity.values()),
        "maps": {
            "total": row["total"],
            "scanned": row["scanned"],
            "with_findings": row["with_findings"],
            "generated": row["generated"],
        },
    }


def maps_with_findings(store) -> list[str]:
    """Ids of readable maps whose latest scan has at least one finding."""
    rows = store._query(
        "SELECT m.id FROM maps m JOIN scans s ON s.map_id = m.id"
        " WHERE (m.parse_error IS NULL OR m.parse_error = '')"
        " AND json_array_length(s.keys_json) > 0 ORDER BY m.id"
    )
    return [r["id"] for r in rows]
