"""Paged, sorted and filtered map queries for the Store."""

import sqlite3
import threading

STATUS_FILTERS = {"all", "error", "warn", "ok", "unscanned", "unreadable"}
_STATUS_RANK = (
    "CASE status WHEN 'unreadable' THEN 0 WHEN 'error' THEN 1 WHEN 'warn' THEN 2"
    " WHEN 'unscanned' THEN 3 ELSE 4 END"
)
# Whitelist: the only text ever placed in ORDER BY. Never built from request input.
SORT_KEYS = {
    "title": "lower(title)",
    "mapper": "lower(mapper)",
    "environment": "lower(environment)",
    "status": _STATUS_RANK,
    "errors": "errors",
    "warnings": "warnings",
    "scanned_at": "scanned_at IS NULL, scanned_at",
}
_TIE_BREAK = "lower(title) ASC, id ASC"
_MAP_VIEW = """
SELECT m.id, m.folder, m.title, m.mapper, m.environment, m.parse_error, s.scanned_at,
  COALESCE((SELECT count(*) FROM json_each(s.keys_json)
            WHERE json_extract(value, '$.severity') = 'error'), 0) AS errors,
  COALESCE((SELECT count(*) FROM json_each(s.keys_json)
            WHERE json_extract(value, '$.severity') != 'error'), 0) AS warnings,
  (SELECT count(*) FROM proposals p WHERE p.map_id = m.id
   AND p.status IN ('approved', 'applying')) AS approved,
  (SELECT count(*) FROM proposals p WHERE p.map_id = m.id AND p.status = 'pending') AS pending,
  CASE WHEN m.parse_error IS NOT NULL AND m.parse_error != '' THEN 'unreadable'
       WHEN s.map_id IS NULL THEN 'unscanned'
       WHEN (SELECT count(*) FROM json_each(s.keys_json)
             WHERE json_extract(value, '$.severity') = 'error') > 0 THEN 'error'
       WHEN (SELECT count(*) FROM json_each(s.keys_json)) > 0 THEN 'warn'
       ELSE 'ok' END AS status
FROM maps m LEFT JOIN scans s ON s.map_id = m.id
"""

_SEARCH = " AND instr(lower(title||char(10)||mapper||char(10)||environment||char(10)||folder), ?)>0"


def _where(filtered: bool, searched: bool) -> str:
    return "WHERE 1=1" + (" AND status=?" if filtered else "") + (_SEARCH if searched else "")


# Every statement is built once, here, from constants. Request input never reaches SQL text:
# it selects a prebuilt statement by key and travels as bound parameters.
_COUNT_SQL = {
    (f, q): f"SELECT count(*) FROM ({_MAP_VIEW}) {_where(f, q)}"  # noqa: S608
    for f in (False, True)
    for q in (False, True)
}
_PAGE_SQL = {
    (f, q, key, d): (
        f"SELECT * FROM ({_MAP_VIEW}) {_where(f, q)}"  # noqa: S608
        f" ORDER BY {expr} {d}, {_TIE_BREAK} LIMIT ? OFFSET ?"
    )
    for f in (False, True)
    for q in (False, True)
    for key, expr in SORT_KEYS.items()
    for d in ("ASC", "DESC")
}
_ONE_SQL = f"SELECT * FROM ({_MAP_VIEW}) WHERE id=?"  # noqa: S608


class MapQueries:
    _lock: threading.Lock
    _db: sqlite3.Connection

    def _query(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        raise NotImplementedError

    def query_maps(
        self,
        offset: int = 0,
        limit: int = 40,
        sort: str = "title",
        order: str = "asc",
        q: str = "",
        status: str = "all",
    ) -> tuple[list[dict], int]:
        """One page of maps with counts and status, plus the total matching the filters."""
        if sort not in SORT_KEYS or order not in ("asc", "desc") or status not in STATUS_FILTERS:
            raise ValueError("invalid sort, order or status")
        needle = q.strip().lower()
        filtered, searched = status != "all", bool(needle)
        args: list = ([status] if filtered else []) + ([needle] if searched else [])
        page = _PAGE_SQL[(filtered, searched, sort, order.upper())]
        with self._lock:
            total = self._db.execute(_COUNT_SQL[(filtered, searched)], args).fetchone()[0]
            rows = self._db.execute(page, [*args, limit, offset]).fetchall()
        return [dict(r) for r in rows], int(total)

    def get_map(self, map_id: str) -> dict | None:
        rows = self._query(_ONE_SQL, (map_id,))
        return dict(rows[0]) if rows else None
