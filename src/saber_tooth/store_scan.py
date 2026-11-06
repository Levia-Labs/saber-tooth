"""Rows of the scans table: findings, the analysis they used, and whether it was missing."""

import json
import sqlite3

SCAN_SQL = (
    "INSERT OR REPLACE INTO scans(map_id, keys_json, analysis, scanned_at, unanalysed)"
    " VALUES(?,?,?,?,?)"
)


def scan_row(map_id: str, scan: dict, now: str) -> tuple:
    flag = int(bool(scan.get("unanalysed")))
    return (map_id, json.dumps(scan["findings"]), scan.get("analysis"), now, flag)


def scan_view(row: sqlite3.Row) -> dict:
    keys, analysis = json.loads(row["keys_json"]), row["analysis"]
    return {"findings": keys, "analysis": analysis, "unanalysed": bool(row["unanalysed"])}
