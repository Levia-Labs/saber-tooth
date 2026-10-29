"""Job rows: the durable queue the worker drains, oldest first."""

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

INTERRUPTED = "interrupted: the service restarted before the job finished"
RECENT_HOURS = 24
RECENT_LIMIT = 50
# Finished rows kept in total. Per-map retention already bounds the table to roughly one row per
# map; this caps libraries with thousands of maps so the jobs table cannot grow without limit.
FINISHED_CAP = 200
# Finished jobs kept per kind when they have no map (generate, learn, downloads before a map).
NO_MAP_KEPT = 5
# Kinds that always act on one map: a finished row without a map is junk, so only the latest stays.
MAP_KINDS = "('scan','fix','apply','crop')"
_FIN = "status IN ('done','failed','cancelled')"
_NEWER = (
    "(n.updated_at > jobs.updated_at OR (n.updated_at = jobs.updated_at AND n.rowid > jobs.rowid))"
)
_PRUNE_MAP_SQL = (
    f"DELETE FROM jobs WHERE {_FIN} AND map_id IS NOT NULL AND EXISTS ("  # noqa: S608
    f"SELECT 1 FROM jobs n WHERE n.map_id = jobs.map_id AND n.{_FIN} AND {_NEWER})"
)
_PRUNE_NO_MAP_SQL = (
    f"DELETE FROM jobs WHERE {_FIN} AND map_id IS NULL AND ("  # noqa: S608
    f"SELECT COUNT(*) FROM jobs n WHERE n.map_id IS NULL AND n.kind = jobs.kind"
    f" AND n.{_FIN} AND {_NEWER}) >= CASE WHEN jobs.kind IN {MAP_KINDS} THEN 1 ELSE ? END"
)
_PRUNE_CAP_SQL = (
    f"DELETE FROM jobs WHERE {_FIN} AND id NOT IN ("  # noqa: S608
    f"SELECT id FROM jobs WHERE {_FIN} ORDER BY updated_at DESC, rowid DESC LIMIT ?)"
)
_DEDUPE_SQL = (
    "SELECT id FROM jobs WHERE map_id=? AND kind=?"
    " AND status IN ('queued','running') ORDER BY created_at, rowid LIMIT 1"
)
_CLAIM_NEXT_SQL = "SELECT id FROM jobs WHERE status='queued' ORDER BY created_at, rowid LIMIT 1"
_RUNNING_SQL = (
    "SELECT j.id, j.kind, j.status, j.error, j.map_id, j.created_at, j.started_at,"
    " j.updated_at, j.progress, j.progress_at, j.args_json,"
    " m.title AS map_title, m.id IS NOT NULL AS map_exists"
    " FROM jobs j LEFT JOIN maps m ON m.id = j.map_id"
    " WHERE j.status='running' ORDER BY j.started_at"
)
_QUEUED_SQL = (
    "SELECT j.id, j.kind, j.status, j.error, j.map_id, j.created_at, j.started_at,"
    " j.updated_at, j.progress, j.progress_at, j.args_json,"
    " m.title AS map_title, m.id IS NOT NULL AS map_exists"
    " FROM jobs j LEFT JOIN maps m ON m.id = j.map_id"
    " WHERE j.status='queued' ORDER BY j.created_at, j.rowid"
)
_RECENT_SQL = (
    "SELECT j.id, j.kind, j.status, j.error, j.map_id, j.created_at, j.started_at,"
    " j.updated_at, j.progress, j.progress_at, j.args_json,"
    " m.title AS map_title, m.id IS NOT NULL AS map_exists"
    " FROM jobs j LEFT JOIN maps m ON m.id = j.map_id"
    " WHERE j.status IN ('done','failed','cancelled')"
    " AND j.updated_at >= ? ORDER BY j.updated_at DESC, j.rowid DESC LIMIT ?"
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _args(raw: str | None) -> dict:
    """Stored arguments as a dict; rows from before the queue have none."""
    try:
        value = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _listed(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["args"] = _args(d.pop("args_json"))
    d["map_exists"] = bool(d["map_exists"])
    return d


class JobRows:
    _lock: threading.Lock
    _db: sqlite3.Connection

    def create_job(
        self,
        kind: str,
        map_id: str | None = None,
        args: dict | None = None,
        dedupe: bool = False,
    ) -> str:
        """Queue a job; with `dedupe`, an active job of this kind on this map is returned."""
        with self._lock:
            if dedupe and map_id is not None:
                row = self._db.execute(_DEDUPE_SQL, (map_id, kind)).fetchone()
                if row:
                    return row["id"]
            job_id = uuid.uuid4().hex
            now = _now()
            self._db.execute(
                "INSERT INTO jobs(id, kind, status, created_at, updated_at, map_id, args_json)"
                " VALUES(?,?,'queued',?,?,?,?)",
                (job_id, kind, now, now, map_id, json.dumps(args or {})),
            )
            self._db.commit()
            return job_id

    def update_job(
        self, id: str, status: str, error: str | None = None, result: Any = None
    ) -> None:
        result_json = None if result is None else json.dumps(result)
        with self._lock:
            cur = self._db.execute(
                "UPDATE jobs SET status=?, error=?, result_json=?, updated_at=? WHERE id=?",
                (status, error, result_json, _now(), id),
            )
            if cur.rowcount and status in ("done", "failed", "cancelled"):
                self._prune_finished()
            self._db.commit()
        if cur.rowcount == 0:
            raise KeyError(id)

    def _prune_finished(self) -> None:
        """Keep each map's latest finished job, a few per kind without a map, and a global cap."""
        self._db.execute(_PRUNE_MAP_SQL)
        self._db.execute(_PRUNE_NO_MAP_SQL, (NO_MAP_KEPT,))
        self._db.execute(_PRUNE_CAP_SQL, (FINISHED_CAP,))

    def prune_finished_jobs(self) -> int:
        """Apply retention to existing rows (startup); idempotent, never touches active jobs."""
        with self._lock:
            before = self._db.total_changes
            self._prune_finished()
            self._db.commit()
            return self._db.total_changes - before

    def job(self, id: str) -> dict:
        with self._lock:
            row = self._db.execute("SELECT * FROM jobs WHERE id=?", (id,)).fetchone()
        if row is None:
            raise KeyError(id)
        d = dict(row)
        raw = d.pop("result_json")
        d["result"] = None if raw is None else json.loads(raw)
        d["args"] = _args(d.pop("args_json"))
        return d

    def claim_next_job(self) -> dict | None:
        """Move the oldest queued job to running and return it; None when the queue is empty."""
        with self._lock:
            row = self._db.execute(_CLAIM_NEXT_SQL).fetchone()
            if row is None:
                return None
            now = _now()
            self._db.execute(
                "UPDATE jobs SET status='running', started_at=?, updated_at=?"
                " WHERE id=? AND status='queued'",
                (now, now, row["id"]),
            )
            self._db.commit()
            raw = self._db.execute(
                "SELECT args_json FROM jobs WHERE id=?", (row["id"],)
            ).fetchone()["args_json"]
        claimed = self.job(row["id"])
        claimed["args_json"] = raw  # the worker fails unreadable JSON instead of running with {}
        return claimed

    def set_job_progress(self, id: str, text: str) -> None:
        now = _now()
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET progress=?, progress_at=?, updated_at=? WHERE id=?",
                (text, now, now, id),
            )
            self._db.commit()

    def cancel_job(self, id: str) -> str:
        """Cancel a queued job; returns "cancelled", or the status that prevented it."""
        with self._lock:
            row = self._db.execute("SELECT status FROM jobs WHERE id=?", (id,)).fetchone()
            if row is None:
                raise KeyError(id)
            if row["status"] != "queued":
                return row["status"]
            self._db.execute(
                "UPDATE jobs SET status='cancelled', updated_at=? WHERE id=?", (_now(), id)
            )
            self._prune_finished()
            self._db.commit()
            return "cancelled"

    def queue_position(self, id: str) -> int | None:
        """1 for the next job to run; None unless the job is queued."""
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) AS n FROM jobs q, jobs j WHERE j.id=? AND j.status='queued'"
                " AND q.status='queued' AND (q.created_at < j.created_at"
                " OR (q.created_at = j.created_at AND q.rowid <= j.rowid))",
                (id,),
            ).fetchone()
        return row["n"] or None

    def job_lists(self, now: datetime | None = None) -> dict[str, list[dict]]:
        cutoff = ((now or datetime.now(UTC)) - timedelta(hours=RECENT_HOURS)).isoformat()
        with self._lock:
            running = self._db.execute(_RUNNING_SQL).fetchall()
            queued = self._db.execute(_QUEUED_SQL).fetchall()
            recent = self._db.execute(_RECENT_SQL, (cutoff, RECENT_LIMIT)).fetchall()
        return {
            "running": [_listed(r) for r in running],
            "queued": [_listed(r) for r in queued],
            "recent": [_listed(r) for r in recent],
        }

    def fail_interrupted_jobs(self) -> int:
        """Fail running jobs, whose worker died with the previous process; queued jobs stay."""
        with self._lock:
            cur = self._db.execute(
                "UPDATE jobs SET status='failed', error=?, updated_at=? WHERE status='running'",
                (INTERRUPTED, _now()),
            )
            self._db.commit()
            return cur.rowcount
