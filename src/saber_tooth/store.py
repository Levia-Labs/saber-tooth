"""SQLite store for maps, jobs and proposals."""

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROPOSAL_STATUSES = {"pending", "approved", "rejected", "applied"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS maps(
    id TEXT PRIMARY KEY, folder TEXT, title TEXT, mapper TEXT,
    environment TEXT, parse_error TEXT, scanned_at TEXT);
CREATE TABLE IF NOT EXISTS jobs(
    id TEXT PRIMARY KEY, kind TEXT, status TEXT, error TEXT,
    result_json TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS proposals(
    id INTEGER PRIMARY KEY AUTOINCREMENT, map_id TEXT, rule TEXT,
    difficulty TEXT, severity TEXT, summary TEXT, ops_json TEXT,
    before_json TEXT, after_json TEXT, status TEXT, created_at TEXT);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path: Path) -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._db.commit()

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
    ) -> None:
        self._exec(
            "INSERT INTO maps(id, folder, title, mapper, environment, parse_error,"
            " scanned_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET"
            " folder=excluded.folder, title=excluded.title, mapper=excluded.mapper,"
            " environment=excluded.environment, parse_error=excluded.parse_error,"
            " scanned_at=excluded.scanned_at",
            (id, folder, title, mapper, environment, parse_error, _now()),
        )

    def list_maps(self) -> list[dict]:
        return [dict(r) for r in self._query("SELECT * FROM maps ORDER BY id")]

    def add_proposals(self, map_id: str, proposals: list[dict]) -> list[int]:
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

    def set_status(self, proposal_id: int, status: str) -> None:
        if status not in PROPOSAL_STATUSES:
            raise ValueError(f"invalid status: {status}")
        cur = self._exec("UPDATE proposals SET status=? WHERE id=?", (status, proposal_id))
        if cur.rowcount == 0:
            raise KeyError(proposal_id)

    def approved(self, map_id: str) -> list[dict]:
        return [p for p in self.proposals(map_id) if p["status"] == "approved"]

    def create_job(self, kind: str) -> str:
        job_id = uuid.uuid4().hex
        now = _now()
        self._exec(
            "INSERT INTO jobs(id, kind, status, created_at, updated_at) VALUES(?,?,'queued',?,?)",
            (job_id, kind, now, now),
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
