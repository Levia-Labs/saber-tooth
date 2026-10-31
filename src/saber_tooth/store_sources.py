"""Source keys: which video or audio file a generated map came from, and which jobs import it."""

import json
import sqlite3
from typing import Any

_ACTIVE_SQL = (
    "SELECT id FROM jobs WHERE kind='generate' AND status IN ('queued','running')"
    " AND json_extract(args_json, '$.source') = ? ORDER BY created_at, rowid LIMIT 1"
)
_DONE_SQL = (
    "SELECT args_json, result_json FROM jobs WHERE kind='generate' AND status='done'"
    " AND result_json IS NOT NULL"
)


class SourceRows:
    _db: sqlite3.Connection

    def _query(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        raise NotImplementedError

    def _exec(self, sql: str, args: tuple = ()) -> Any:
        raise NotImplementedError

    def set_source(self, map_id: str, source: str) -> None:
        """Record the source a library map was generated from; survives a re-index."""
        self._exec("UPDATE maps SET source=? WHERE id=?", (source, map_id))

    def find_source(self, source: str) -> dict | None:
        """The library map generated from this source, or None."""
        rows = self._query("SELECT id, folder, title FROM maps WHERE source = ? LIMIT 1", (source,))
        return dict(rows[0]) if rows else None

    def active_source_job(self, source: str) -> str | None:
        """The id of a queued or running generate job for this source, or None."""
        rows = self._query(_ACTIVE_SQL, (source,))
        return rows[0]["id"] if rows else None

    def merge_job_args(self, job_id: str, extra: dict) -> None:
        """Add keys to a job's stored arguments."""
        rows = self._query("SELECT args_json FROM jobs WHERE id=?", (job_id,))
        if not rows:
            return
        try:
            args = json.loads(rows[0]["args_json"] or "{}")
        except ValueError:
            args = {}
        args = {**(args if isinstance(args, dict) else {}), **extra}
        self._exec("UPDATE jobs SET args_json=? WHERE id=?", (json.dumps(args), job_id))

    def backfill_sources(self, source_of: Any) -> int:
        """Give maps made before sources existed the source of their finished generate job.

        `source_of(args)` returns the source key for the job's arguments, or None.
        """
        done = 0
        for row in self._query(_DONE_SQL):
            try:
                args, result = json.loads(row["args_json"] or "{}"), json.loads(row["result_json"])
            except ValueError:
                continue
            source = source_of(args) if isinstance(args, dict) else None
            map_id = result.get("map_id") if isinstance(result, dict) else None
            if source and isinstance(map_id, str):
                cur = self._exec(
                    "UPDATE maps SET source=? WHERE id=? AND (source IS NULL OR source='')",
                    (source, map_id),
                )
                done += cur.rowcount if cur is not None else 0
        return done
