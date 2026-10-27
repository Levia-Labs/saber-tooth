"""SQLite store for maps, jobs and proposals."""

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from saber_tooth.store_maps import MapQueries

PROPOSAL_STATUSES = {"pending", "approved", "rejected", "applied"}
CLAIMED = "applying"  # internal: approved rows an apply has claimed; the API shows "approved"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS maps(
    id TEXT PRIMARY KEY, folder TEXT, title TEXT, mapper TEXT,
    environment TEXT, parse_error TEXT, scanned_at TEXT, bpm REAL, duration_s REAL, levels INTEGER);
CREATE TABLE IF NOT EXISTS jobs(
    id TEXT PRIMARY KEY, kind TEXT, status TEXT, error TEXT,
    result_json TEXT, created_at TEXT, updated_at TEXT, map_id TEXT);
CREATE TABLE IF NOT EXISTS proposals(
    id INTEGER PRIMARY KEY AUTOINCREMENT, map_id TEXT, rule TEXT,
    difficulty TEXT, severity TEXT, summary TEXT, ops_json TEXT,
    before_json TEXT, after_json TEXT, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS scans(
    map_id TEXT PRIMARY KEY, keys_json TEXT, analysis TEXT, scanned_at TEXT);
"""
_INDEXES = "CREATE INDEX IF NOT EXISTS jobs_map ON jobs(map_id, status);"
# Columns added after the first release: (table, column, statement). Added in place when missing.
_MIGRATIONS = (
    ("maps", "bpm", "ALTER TABLE maps ADD COLUMN bpm REAL"),
    ("maps", "duration_s", "ALTER TABLE maps ADD COLUMN duration_s REAL"),
    ("maps", "levels", "ALTER TABLE maps ADD COLUMN levels INTEGER"),
    ("maps", "bs_id", "ALTER TABLE maps ADD COLUMN bs_id TEXT"),
    ("maps", "bs_hash", "ALTER TABLE maps ADD COLUMN bs_hash TEXT"),
    ("jobs", "map_id", "ALTER TABLE jobs ADD COLUMN map_id TEXT"),
)


class ProposalApplied(Exception):
    """A status change was refused because the proposal is already applied."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Store(MapQueries):
    def __init__(self, path: Path) -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._migrate()
            self._db.executescript(_INDEXES)
            self._db.commit()

    def _migrate(self) -> None:
        for table, column, statement in _MIGRATIONS:
            have = self._db.execute("SELECT name FROM pragma_table_info(?)", (table,)).fetchall()
            if column not in {r["name"] for r in have}:
                self._db.execute(statement)

    def _query(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    def _exec(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._db.execute(sql, args)
            self._db.commit()
            return cur

    def upsert_map(
        self,
        id: str,
        folder: str,
        title: str,
        mapper: str,
        environment: str,
        parse_error: str | None,
        bpm: float | None = None,
        duration_s: float | None = None,
        levels: int | None = None,
    ) -> None:
        self._exec(
            "INSERT INTO maps(id, folder, title, mapper, environment, parse_error,"
            " scanned_at, bpm, duration_s, levels) VALUES(?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " folder=excluded.folder, title=excluded.title, mapper=excluded.mapper,"
            " environment=excluded.environment, parse_error=excluded.parse_error,"
            " scanned_at=excluded.scanned_at, bpm=excluded.bpm, duration_s=excluded.duration_s,"
            " levels=excluded.levels",
            (id, folder, title, mapper, environment, parse_error, _now(), bpm, duration_s, levels),
        )

    def list_maps(self) -> list[dict]:
        return [dict(r) for r in self._query("SELECT * FROM maps ORDER BY id")]

    def add_proposals(self, map_id: str, proposals: list[dict]) -> list[int]:
        return self._insert(map_id, proposals, delete_open=False, scan=None)

    def replace_open_proposals(
        self, map_id: str, proposals: list[dict], scan: dict | None = None
    ) -> list[int]:
        """Atomically drop pending and approved proposals, insert new ones, save the scan.

        scan is {"findings": list[dict], "analysis": str | None}; history (rejected, applied) stays.
        """
        return self._insert(map_id, proposals, delete_open=True, scan=scan)

    def _insert(
        self, map_id: str, proposals: list[dict], delete_open: bool, scan: dict | None
    ) -> list[int]:
        now = _now()
        rows = [
            (
                map_id,
                p["rule"],
                p["difficulty"],
                p["severity"],
                p["summary"],
                json.dumps(p["ops"]),
                json.dumps(p["before"]),
                json.dumps(p["after"]),
                now,
            )
            for p in proposals
        ]
        ids: list[int] = []
        with self._lock:
            try:
                if delete_open:
                    self._db.execute(
                        "DELETE FROM proposals WHERE map_id=? AND status IN ('pending','approved')",
                        (map_id,),
                    )
                if scan is not None:
                    self._db.execute(
                        "INSERT OR REPLACE INTO scans(map_id, keys_json, analysis, scanned_at)"
                        " VALUES(?,?,?,?)",
                        (map_id, json.dumps(scan["findings"]), scan.get("analysis"), now),
                    )
                for row in rows:
                    cur = self._db.execute(
                        "INSERT INTO proposals(map_id, rule, difficulty, severity, summary,"
                        " ops_json, before_json, after_json, status, created_at)"
                        " VALUES(?,?,?,?,?,?,?,?,'pending',?)",
                        row,
                    )
                    ids.append(int(cur.lastrowid))
                self._db.commit()
            except BaseException:
                self._db.rollback()
                raise
        return ids

    @staticmethod
    def _proposal(row: sqlite3.Row) -> dict:
        d = dict(row)
        for key in ("ops", "before", "after"):
            d[key] = json.loads(d.pop(f"{key}_json"))
        return d

    def proposals(self, map_id: str) -> list[dict]:
        rows = self._query("SELECT * FROM proposals WHERE map_id=? ORDER BY id", (map_id,))
        return [self._proposal(r) for r in rows]

    def proposal(self, proposal_id: int) -> dict | None:
        rows = self._query("SELECT * FROM proposals WHERE id=?", (proposal_id,))
        return self._proposal(rows[0]) if rows else None

    def set_status(self, proposal_id: int, status: str) -> None:
        if status not in PROPOSAL_STATUSES:
            raise ValueError(f"invalid status: {status}")
        cur = self._exec(
            "UPDATE proposals SET status=? WHERE id=? AND status NOT IN ('applied', 'applying')",
            (status, proposal_id),
        )
        if cur.rowcount == 0:
            if self._query("SELECT 1 FROM proposals WHERE id=?", (proposal_id,)):
                raise ProposalApplied(proposal_id)
            raise KeyError(proposal_id)

    def claim(self, proposal_ids: list[int]) -> bool:
        """Atomically move all of these approved proposals to applying, or none."""
        with self._lock:
            try:
                for pid in proposal_ids:
                    cur = self._db.execute(
                        "UPDATE proposals SET status=? WHERE id=? AND status='approved'",
                        (CLAIMED, pid),
                    )
                    if cur.rowcount == 0:
                        self._db.rollback()
                        return False
                self._db.commit()
                return True
            except BaseException:
                self._db.rollback()
                raise

    def release(self, proposal_ids: list[int]) -> None:
        """Return claimed proposals to approved after a failed apply."""
        with self._lock:
            for pid in proposal_ids:
                self._db.execute(
                    "UPDATE proposals SET status='approved' WHERE id=? AND status=?",
                    (pid, CLAIMED),
                )
            self._db.commit()

    def mark_applied(self, proposal_ids: list[int]) -> None:
        """Set every approved or claimed proposal applied in one transaction."""
        with self._lock:
            try:
                for pid in proposal_ids:
                    self._db.execute(
                        "UPDATE proposals SET status='applied'"
                        " WHERE id=? AND status IN ('approved', ?)",
                        (pid, CLAIMED),
                    )
                self._db.commit()
            except BaseException:
                self._db.rollback()
                raise

    def scan_info(self, map_id: str) -> dict | None:
        rows = self._query("SELECT * FROM scans WHERE map_id=?", (map_id,))
        if not rows:
            return None
        return {"findings": json.loads(rows[0]["keys_json"]), "analysis": rows[0]["analysis"]}

    def prune_maps(self, keep: set[str]) -> None:
        """Drop map rows (and their scans) whose id is not in keep."""
        with self._lock:
            ids = [r["id"] for r in self._db.execute("SELECT id FROM maps").fetchall()]
            for mid in ids:
                if mid not in keep:
                    self._db.execute("DELETE FROM maps WHERE id=?", (mid,))
                    self._db.execute("DELETE FROM scans WHERE map_id=?", (mid,))
            self._db.commit()

    def approved(self, map_id: str) -> list[dict]:
        return [p for p in self.proposals(map_id) if p["status"] == "approved"]

    def create_job(self, kind: str, map_id: str | None = None) -> str:
        job_id = uuid.uuid4().hex
        now = _now()
        self._exec(
            "INSERT INTO jobs(id, kind, status, created_at, updated_at, map_id)"
            " VALUES(?,?,'queued',?,?,?)",
            (job_id, kind, now, now, map_id),
        )
        return job_id

    def update_job(
        self, id: str, status: str, error: str | None = None, result: Any = None
    ) -> None:
        result_json = None if result is None else json.dumps(result)
        cur = self._exec(
            "UPDATE jobs SET status=?, error=?, result_json=?, updated_at=? WHERE id=?",
            (status, error, result_json, _now(), id),
        )
        if cur.rowcount == 0:
            raise KeyError(id)

    def job(self, id: str) -> dict:
        rows = self._query("SELECT * FROM jobs WHERE id=?", (id,))
        if not rows:
            raise KeyError(id)
        d = dict(rows[0])
        raw = d.pop("result_json")
        d["result"] = None if raw is None else json.loads(raw)
        return d
