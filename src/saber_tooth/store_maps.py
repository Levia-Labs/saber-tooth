"""Paged, sorted and filtered map queries for the Store."""

import functools
import sqlite3
import threading

STATUS_VALUES = (
    "unreadable", "error", "warn", "scanning", "applying", "queued", "unscanned", "ok",
)  # fmt: skip
STATUS_FILTERS = {"all", *STATUS_VALUES}
MAX_ENVS = 50
_STATUS_RANK = (
    "CASE status " + " ".join(f"WHEN '{v}' THEN {i}" for i, v in enumerate(STATUS_VALUES)) + " END"
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
    "bpm": "bpm IS NULL, bpm",
    "duration": "duration_s IS NULL, duration_s",
}
_TIE_BREAK = "lower(title) ASC, id ASC"
_MAP_VIEW = """
SELECT m.id, m.folder, m.title, m.mapper, m.environment, m.parse_error, s.scanned_at,
  m.bpm, m.duration_s,
  COALESCE((SELECT count(*) FROM json_each(s.keys_json)
            WHERE json_extract(value, '$.severity') = 'error'), 0) AS errors,
  COALESCE((SELECT count(*) FROM json_each(s.keys_json)
            WHERE json_extract(value, '$.severity') != 'error'), 0) AS warnings,
  (SELECT count(*) FROM proposals p WHERE p.map_id = m.id
   AND p.status IN ('approved', 'applying')) AS approved,
  (SELECT count(*) FROM proposals p WHERE p.map_id = m.id AND p.status = 'pending') AS pending,
  j.id AS job_id, j.kind AS job_kind, j.status AS job_status,
  CASE WHEN m.parse_error IS NOT NULL AND m.parse_error != '' THEN 'unreadable'
       WHEN j.status = 'running' AND j.kind = 'scan' THEN 'scanning'
       WHEN j.status = 'running' THEN 'applying'
       WHEN j.status = 'queued' THEN 'queued'
       WHEN s.map_id IS NULL THEN 'unscanned'
       WHEN (SELECT count(*) FROM json_each(s.keys_json)
             WHERE json_extract(value, '$.severity') = 'error') > 0 THEN 'error'
       WHEN (SELECT count(*) FROM json_each(s.keys_json)) > 0 THEN 'warn'
       ELSE 'ok' END AS status
FROM maps m LEFT JOIN scans s ON s.map_id = m.id
LEFT JOIN jobs j ON j.id = (
  SELECT a.id FROM jobs a WHERE a.map_id = m.id AND a.kind IN ('scan', 'apply')
  AND a.status IN ('queued', 'running')
  ORDER BY (a.status = 'running') DESC, a.created_at DESC, a.id LIMIT 1)
"""

_SEARCH = {
    "all": "instr(lower(title||char(10)||mapper||char(10)||environment||char(10)||folder), ?)>0",
    "name": "instr(lower(title||char(10)||mapper), ?)>0",
}
Q_FIELDS = {"title", "mapper"}


def _marks(n: int) -> str:
    return ",".join("?" * n)


def _where(n_status: int, n_env: int, search: str | None) -> str:
    parts = ["1=1"]
    if n_status:
        parts.append(f"status IN ({_marks(n_status)})")
    if n_env:
        parts.append(f"environment IN ({_marks(n_env)})")
    if search:
        parts.append(_SEARCH[search])
    return "WHERE " + " AND ".join(parts)


# Statement text is assembled only from constants, whitelisted keys and runs of "?". Request input
# never reaches SQL text: it selects a statement by key and travels as bound parameters.
@functools.cache
def _count_sql(n_status: int, n_env: int, search: str | None) -> str:
    return f"SELECT count(*) FROM ({_MAP_VIEW}) {_where(n_status, n_env, search)}"  # noqa: S608


@functools.cache
def _page_sql(n_status: int, n_env: int, search: str | None, key: str, direction: str) -> str:
    order = SORT_KEYS[key]
    d = "DESC" if direction == "DESC" else "ASC"
    return (
        f"SELECT * FROM ({_MAP_VIEW}) {_where(n_status, n_env, search)}"  # noqa: S608
        f" ORDER BY {order} {d}, {_TIE_BREAK} LIMIT ? OFFSET ?"
    )


_ONE_SQL = f"SELECT * FROM ({_MAP_VIEW}) WHERE id=?"  # noqa: S608
_FACET_SQL = f"SELECT status, environment FROM ({_MAP_VIEW})"  # noqa: S608


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
        status: tuple[str, ...] | str = (),
        env: tuple[str, ...] = (),
        q_fields: str = "all",
    ) -> tuple[list[dict], int]:
        """One page of maps with counts and status, plus the total matching the filters."""
        statuses = (status,) if isinstance(status, str) else tuple(status)
        if "all" in statuses:
            statuses = ()
        statuses = tuple(dict.fromkeys(statuses))
        envs = tuple(dict.fromkeys(env))
        if (
            sort not in SORT_KEYS
            or order not in ("asc", "desc")
            or not set(statuses) <= set(STATUS_VALUES)
            or len(envs) > MAX_ENVS
            or q_fields not in _SEARCH
        ):
            raise ValueError("invalid sort, order, status, env or q_fields")
        needle = q.strip().lower()
        search = q_fields if needle else None
        args: list = [*statuses, *envs, *([needle] if needle else [])]
        count = _count_sql(len(statuses), len(envs), search)
        page = _page_sql(len(statuses), len(envs), search, sort, order.upper())
        with self._lock:
            total = self._db.execute(count, args).fetchone()[0]
            rows = self._db.execute(page, [*args, limit, offset]).fetchall()
        return [dict(r) for r in rows], int(total)

    def facets(self) -> dict:
        """Counts per status and per environment over every map, ignoring any filter."""
        rows = self._query(_FACET_SQL)
        status: dict[str, int] = {}
        envs: dict[str, int] = {}
        for r in rows:
            status[r["status"]] = status.get(r["status"], 0) + 1
            if r["environment"]:
                envs[r["environment"]] = envs.get(r["environment"], 0) + 1
        ordered = sorted(envs.items(), key=lambda kv: (-kv[1], kv[0].lower(), kv[0]))
        return {
            "status": {v: status.get(v, 0) for v in STATUS_VALUES},
            "environments": [{"name": n, "count": c} for n, c in ordered],
            "total": len(rows),
        }

    def get_map(self, map_id: str) -> dict | None:
        rows = self._query(_ONE_SQL, (map_id,))
        return dict(rows[0]) if rows else None
