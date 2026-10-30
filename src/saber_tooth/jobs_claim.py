"""Claim the oldest queued job whose map no running job is already working on."""

from collections.abc import Collection

from saber_tooth.store import Store, _now


def claim_job(store: Store, busy_maps: Collection[str]) -> dict | None:
    """Move the oldest eligible queued job to running and return it, None when nothing can run.

    A job is skipped while another job on its map is running; it keeps its place in the queue.
    """
    with store._lock:
        rows = store._db.execute(
            "SELECT id, map_id FROM jobs WHERE status='queued' ORDER BY created_at, rowid"
        ).fetchall()
        pick = next((r for r in rows if r["map_id"] is None or r["map_id"] not in busy_maps), None)
        if pick is None:
            return None
        now = _now()
        store._db.execute(
            "UPDATE jobs SET status='running', started_at=?, updated_at=? WHERE id=?",
            (now, now, pick["id"]),
        )
        store._db.commit()
        raw = store._db.execute("SELECT args_json FROM jobs WHERE id=?", (pick["id"],)).fetchone()
    claimed = store.job(pick["id"])
    claimed["args_json"] = raw["args_json"]
    return claimed
