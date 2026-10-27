"""SQLite cache of BeatSaver map details (24 h) and query result pages (10 min)."""

import json
import sqlite3
import threading
import time
from collections.abc import Callable
from pathlib import Path

from saber_tooth.beatsaver.models import BsMap

MAP_TTL = 24 * 3600.0
QUERY_TTL = 600.0
_SCHEMA = """
CREATE TABLE IF NOT EXISTS bs_maps(
    id TEXT PRIMARY KEY, hash TEXT, json TEXT, fetched_at REAL);
CREATE TABLE IF NOT EXISTS bs_queries(
    key TEXT, page INTEGER, ids TEXT, fetched_at REAL, PRIMARY KEY(key, page));
CREATE INDEX IF NOT EXISTS bs_maps_hash ON bs_maps(hash);
"""
_CHUNK = 500


class BsCache:
    """Tables are created in place with IF NOT EXISTS, so an existing database is kept as is."""

    def __init__(self, db_path: Path, clock: Callable[[], float] = time.time) -> None:
        self.clock = clock
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False, timeout=15)
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._db.commit()

    def put_maps(self, maps: list[BsMap]) -> None:
        now = self.clock()
        rows = [(m.id, m.hash, json.dumps(m.to_dict()), now) for m in maps if m.id]
        with self._lock:
            self._db.executemany(
                "INSERT INTO bs_maps(id, hash, json, fetched_at) VALUES(?,?,?,?)"
                " ON CONFLICT(id) DO UPDATE SET hash=excluded.hash, json=excluded.json,"
                " fetched_at=excluded.fetched_at",
                rows,
            )
            self._db.commit()

    def get_maps(self, ids: list[str]) -> dict[str, BsMap]:
        """Fresh cached maps by id; entries older than 24 h and unreadable rows are skipped."""
        floor = self.clock() - MAP_TTL
        found: dict[str, BsMap] = {}
        for start in range(0, len(ids), _CHUNK):
            part = ids[start : start + _CHUNK]
            with self._lock:
                rows = self._db.execute(
                    "SELECT id, json FROM bs_maps WHERE fetched_at >= ?"
                    " AND id IN (SELECT value FROM json_each(?))",
                    (floor, json.dumps(part)),
                ).fetchall()
            for mid, raw in rows:
                try:
                    found[mid] = BsMap.from_dict(json.loads(raw))
                except (ValueError, TypeError, KeyError):
                    continue
        return found

    def put_query(self, key: str, page: int, ids: list[str]) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO bs_queries(key, page, ids, fetched_at) VALUES(?,?,?,?)"
                " ON CONFLICT(key, page) DO UPDATE SET ids=excluded.ids,"
                " fetched_at=excluded.fetched_at",
                (key, page, json.dumps(ids), self.clock()),
            )
            self._db.commit()

    def get_query(self, key: str, page: int) -> list[str] | None:
        """Ids of a cached result page, or None when absent or older than 10 min."""
        with self._lock:
            row = self._db.execute(
                "SELECT ids FROM bs_queries WHERE key=? AND page=? AND fetched_at >= ?",
                (key, page, self.clock() - QUERY_TTL),
            ).fetchone()
        if row is None:
            return None
        try:
            ids = json.loads(row[0])
        except ValueError:
            return None
        return ids if isinstance(ids, list) else None

    def prune(self) -> None:
        """Drop expired rows."""
        with self._lock:
            self._db.execute("DELETE FROM bs_maps WHERE fetched_at < ?", (self.clock() - MAP_TTL,))
            self._db.execute(
                "DELETE FROM bs_queries WHERE fetched_at < ?", (self.clock() - QUERY_TTL,)
            )
            self._db.commit()
