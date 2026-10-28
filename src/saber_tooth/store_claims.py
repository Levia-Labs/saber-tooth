"""Claiming approved proposals for an apply, and superseding stale ones."""

import sqlite3
import threading
from datetime import UTC, datetime

CLAIMED = "applying"  # internal: approved rows an apply has claimed; the API shows "approved"


INTERRUPTED = "interrupted: the service restarted before the job finished"


class ProposalClaims:
    _lock: threading.Lock
    _db: sqlite3.Connection

    def fail_interrupted_jobs(self) -> int:
        """Fail queued and running jobs; their worker threads died with the previous process."""
        now = datetime.now(UTC).isoformat()
        with self._lock:
            cur = self._db.execute(
                "UPDATE jobs SET status='failed', error=?, updated_at=?"
                " WHERE status IN ('queued','running')",
                (INTERRUPTED, now),
            )
            self._db.commit()
            return cur.rowcount

    def _add_one(self, map_id: str, p: dict) -> int:
        raise NotImplementedError

    def supersede(self, proposal_id: int, replacement: dict | None = None) -> int | None:
        """Mark an approved proposal superseded; with a replacement, add it as a new pending
        proposal that replaces it and return its id. Nothing changes if it is no longer approved."""
        with self._lock:
            try:
                cur = self._db.execute(
                    "UPDATE proposals SET status='superseded' WHERE id=? AND status='approved'",
                    (proposal_id,),
                )
                new_id = None
                if cur.rowcount and replacement is not None:
                    old = self._db.execute(
                        "SELECT map_id FROM proposals WHERE id=?", (proposal_id,)
                    ).fetchone()
                    new_id = self._add_one(old["map_id"], {**replacement, "replaces": proposal_id})
                self._db.commit()
                return new_id
            except BaseException:
                self._db.rollback()
                raise

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
