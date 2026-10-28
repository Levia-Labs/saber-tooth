"""Paged, sorted and filtered map queries for the Store."""

import functools
import sqlite3
import threading

STATUS_VALUES = (
    "unreadable", "error", "warn", "scanning", "applying", "fixing", "queued", "incomplete",
    "unscanned", "ok",
)  # fmt: skip
FIXED_COPY_SUFFIX = " [saber-tooth]"  # folder suffix Fix gives the copy it writes
STATUS_FILTERS = {"all", *STATUS_VALUES}
MAX_ENVS = 50
MAX_MAPPERS = 50
LEVEL_NAMES = ("Easy", "Normal", "Hard", "Expert", "ExpertPlus")  # bit i of maps.levels
ALL_LEVELS = (1 << len(LEVEL_NAMES)) - 1  # mask with every Standard difficulty present
LEVEL_MODES = ("any", "all")
# (query keyword, SQL column, comparison) of the range filters, in bound order
RANGES = (
    ("duration_min", "duration_s", ">="),
    ("duration_max", "duration_s", "<="),
    ("bpm_min", "bpm", ">="),
    ("bpm_max", "bpm", "<="),
)
RANGE_LIMITS = {"duration": (0.0, 7200.0), "bpm": (0.0, 1000.0)}


def level_mask(names) -> int:
    """Bitmask of the known level names; unknown names are ignored."""
    return sum(1 << i for i, n in enumerate(LEVEL_NAMES) if n in set(names))


def _levels_bits(col: str = "levels") -> str:
    return " + ".join(f"(({col} >> {i}) & 1)" for i in range(len(LEVEL_NAMES)))


def _levels_height() -> str:
    return " + ".join(f"(levels >= {1 << i})" for i in range(len(LEVEL_NAMES)))


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
    # highest level present, then how many levels; maps without levels sort last either way
    "levels": f"levels IS NULL OR levels = 0, ({_levels_height()}) * 8 + ({_levels_bits()})",
}
_TIE_BREAK = "lower(title) ASC, id ASC"
_MAP_VIEW = f"""
SELECT m.id, m.folder, m.title, m.mapper, m.environment, m.parse_error, s.scanned_at,
  m.bpm, m.duration_s, m.levels,
  COALESCE((SELECT count(*) FROM json_each(s.keys_json)
            WHERE json_extract(value, '$.severity') = 'error'), 0) AS errors,
  COALESCE((SELECT count(*) FROM json_each(s.keys_json)
            WHERE json_extract(value, '$.severity') != 'error'), 0) AS warnings,
  (SELECT count(*) FROM proposals p WHERE p.map_id = m.id
   AND p.status IN ('approved', 'applying')) AS approved,
  (SELECT count(*) FROM proposals p WHERE p.map_id = m.id AND p.status = 'pending') AS pending,
  (SELECT f.id FROM maps f WHERE f.folder = m.folder || '{FIXED_COPY_SUFFIX}') AS fixed_copy_id,
  (SELECT f.folder FROM maps f
   WHERE f.folder = m.folder || '{FIXED_COPY_SUFFIX}') AS fixed_copy_folder,
  (SELECT o.id FROM maps o WHERE m.folder = o.folder || '{FIXED_COPY_SUFFIX}') AS original_id,
  (SELECT o.folder FROM maps o
   WHERE m.folder = o.folder || '{FIXED_COPY_SUFFIX}') AS original_folder,
  j.id AS job_id, j.kind AS job_kind, j.status AS job_status,
  CASE WHEN m.parse_error IS NOT NULL AND m.parse_error != '' THEN 'unreadable'
       WHEN j.status = 'running' AND j.kind = 'scan' THEN 'scanning'
       WHEN j.status = 'running' AND j.kind = 'fix' THEN 'fixing'
       WHEN j.status = 'running' THEN 'applying'
       WHEN j.status = 'queued' THEN 'queued'
       WHEN s.map_id IS NULL AND (m.levels IS NULL OR m.levels != {ALL_LEVELS}) THEN 'incomplete'
       WHEN s.map_id IS NULL THEN 'unscanned'
       WHEN (SELECT count(*) FROM json_each(s.keys_json)
             WHERE json_extract(value, '$.severity') = 'error') > 0 THEN 'error'
       WHEN (SELECT count(*) FROM json_each(s.keys_json)) > 0 THEN 'warn'
       ELSE 'ok' END AS status
FROM maps m LEFT JOIN scans s ON s.map_id = m.id
LEFT JOIN jobs j ON j.id = (
  SELECT a.id FROM jobs a WHERE a.map_id = m.id AND a.kind IN ('scan', 'apply', 'fix')
  AND a.status IN ('queued', 'running')
  ORDER BY (a.status = 'running') DESC, a.created_at DESC, a.id LIMIT 1)
"""  # noqa: S608 - interpolates only the constants ALL_LEVELS, FIXED_COPY_SUFFIX

# Lists and facets hide an original once its fixed copy exists; by-id lookups still find it.
_VISIBLE = "fixed_copy_id IS NULL"

_SEARCH = {
    "all": "instr(lower(title||char(10)||mapper||char(10)||environment||char(10)||folder), ?)>0",
    "name": "instr(lower(title||char(10)||mapper), ?)>0",
    "title": "instr(lower(title), ?)>0",
    "mapper": "instr(lower(mapper), ?)>0",
}
Q_FIELDS = {"title", "mapper"}


def _marks(n: int) -> str:
    return ",".join("?" * n)


_LEVEL_WHERE = {"any": "(levels & ?) != 0", "all": "(levels & ?) = ?"}


def _where(shape: tuple) -> str:
    n_status, n_env, n_mapper, level_mode, search, ranges = shape
    parts = [_VISIBLE]
    if n_status:
        parts.append(f"status IN ({_marks(n_status)})")
    if n_env:
        parts.append(f"environment IN ({_marks(n_env)})")
    if n_mapper:
        parts.append(f"mapper IN ({_marks(n_mapper)})")
    if level_mode:
        parts.append(_LEVEL_WHERE[level_mode])
    if search:
        parts.append(_SEARCH[search])
    # a bound excludes maps without the value, since NULL compares false
    parts.extend(f"{col} {op} ?" for (_, col, op), used in zip(RANGES, ranges, strict=True) if used)
    return "WHERE " + " AND ".join(parts)


# Statement text is assembled only from constants, whitelisted keys and runs of "?". Request input
# never reaches SQL text: it selects a statement by key and travels as bound parameters.
@functools.cache
def _count_sql(shape: tuple) -> str:
    return f"SELECT count(*) FROM ({_MAP_VIEW}) {_where(shape)}"  # noqa: S608


@functools.cache
def _page_sql(shape: tuple, key: str, direction: str) -> str:
    order = SORT_KEYS[key]
    d = "DESC" if direction == "DESC" else "ASC"
    return (
        f"SELECT * FROM ({_MAP_VIEW}) {_where(shape)}"  # noqa: S608
        f" ORDER BY {order} {d}, {_TIE_BREAK} LIMIT ? OFFSET ?"
    )


_ONE_SQL = f"SELECT * FROM ({_MAP_VIEW}) WHERE id=?"  # noqa: S608
_FACET_SQL = (
    f"SELECT status, environment, mapper, levels, bpm, duration_s FROM ({_MAP_VIEW})"  # noqa: S608
    f" WHERE {_VISIBLE}"
)


def _ranked(counts: dict[str, int]) -> list[dict]:
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower(), kv[0]))
    return [{"name": n, "count": c} for n, c in ordered]


def _span(values: list) -> dict:
    """Smallest and largest value, or nulls when no map has one."""
    return {"min": min(values), "max": max(values)} if values else {"min": None, "max": None}


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
        mapper: tuple[str, ...] = (),
        level: tuple[str, ...] = (),
        level_mode: str = "any",
        duration_min: float | None = None,
        duration_max: float | None = None,
        bpm_min: float | None = None,
        bpm_max: float | None = None,
    ) -> tuple[list[dict], int]:
        """One page of maps with counts and status, plus the total matching the filters."""
        statuses = (status,) if isinstance(status, str) else tuple(status)
        if "all" in statuses:
            statuses = ()
        statuses = tuple(dict.fromkeys(statuses))
        envs = tuple(dict.fromkeys(env))
        mappers = tuple(dict.fromkeys(mapper))
        levels = tuple(dict.fromkeys(level))
        if (
            sort not in SORT_KEYS
            or order not in ("asc", "desc")
            or not set(statuses) <= set(STATUS_VALUES)
            or len(envs) > MAX_ENVS
            or q_fields not in _SEARCH
            or len(mappers) > MAX_MAPPERS
            or not set(levels) <= set(LEVEL_NAMES)
            or level_mode not in LEVEL_MODES
        ):
            raise ValueError("invalid sort, order, status, env, mapper, level or q_fields")
        bounds = (duration_min, duration_max, bpm_min, bpm_max)
        for (name, _, _), value in zip(RANGES, bounds, strict=True):
            low, high = RANGE_LIMITS[name.split("_")[0]]
            if value is not None and not low <= value <= high:  # NaN fails the comparison too
                raise ValueError(f"{name} must be from {low:g} to {high:g}")
        ranges = tuple(v is not None for v in bounds)
        needle = q.strip().lower()
        search = q_fields if needle else None
        mask = level_mask(levels)
        mode = level_mode if levels else None
        mask_args = [] if not mode else [mask] if mode == "any" else [mask, mask]
        args: list = [*statuses, *envs, *mappers, *mask_args, *([needle] if needle else [])]
        args += [v for v in bounds if v is not None]
        shape = (len(statuses), len(envs), len(mappers), mode, search, ranges)
        count = _count_sql(shape)
        page = _page_sql(shape, sort, order.upper())
        with self._lock:
            total = self._db.execute(count, args).fetchone()[0]
            rows = self._db.execute(page, [*args, limit, offset]).fetchall()
        return [dict(r) for r in rows], int(total)

    def facets(self) -> dict:
        """Counts per status, environment, mapper and level over every map, ignoring any filter."""
        rows = self._query(_FACET_SQL)
        status: dict[str, int] = {}
        envs: dict[str, int] = {}
        mappers: dict[str, int] = {}
        levels = dict.fromkeys(LEVEL_NAMES, 0)
        durations = [r["duration_s"] for r in rows if r["duration_s"] is not None]
        bpms = [r["bpm"] for r in rows if r["bpm"] is not None]
        for r in rows:
            status[r["status"]] = status.get(r["status"], 0) + 1
            if r["environment"]:
                envs[r["environment"]] = envs.get(r["environment"], 0) + 1
            if r["mapper"]:
                mappers[r["mapper"]] = mappers.get(r["mapper"], 0) + 1
            for i, name in enumerate(LEVEL_NAMES):
                if (r["levels"] or 0) >> i & 1:
                    levels[name] += 1
        return {
            "status": {v: status.get(v, 0) for v in STATUS_VALUES},
            "environments": _ranked(envs),
            "mappers": _ranked(mappers),
            "levels": levels,
            "duration": _span(durations),
            "bpm": _span(bpms),
            "total": len(rows),
        }

    def get_map(self, map_id: str) -> dict | None:
        rows = self._query(_ONE_SQL, (map_id,))
        return dict(rows[0]) if rows else None

    def set_bs(self, map_id: str, bs_id: str, bs_hash: str) -> None:
        """Record the BeatSaver key and hash a library map was installed from."""
        self._exec("UPDATE maps SET bs_id=?, bs_hash=? WHERE id=?", (bs_id, bs_hash, map_id))

    def bs_rows(self) -> list[dict]:
        """Library maps with their folder and recorded BeatSaver key and hash."""
        rows = self._query("SELECT id, folder, bs_id, bs_hash FROM maps")
        return [dict(r) for r in rows]

    def find_bs(self, bs_id: str, bs_hash: str) -> dict | None:
        """A library map with this BeatSaver key or hash, or whose folder starts with the key."""
        rows = self._query(
            "SELECT id, folder FROM maps WHERE bs_id = ? OR (? != '' AND bs_hash = ?)"
            " OR folder = ? OR instr(folder, ?) = 1 LIMIT 1",
            (bs_id, bs_hash, bs_hash, bs_id, f"{bs_id} ("),
        )
        return dict(rows[0]) if rows else None
