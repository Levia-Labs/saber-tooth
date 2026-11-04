"""Row removal for deleted maps: maps, scans, proposals and jobs in one transaction."""

import sqlite3
from typing import Any

_TABLES = (("maps", "id"), ("scans", "map_id"), ("proposals", "map_id"), ("jobs", "map_id"))


class DeleteRows:
    _db: sqlite3.Connection
    _lock: Any

    def delete_map(self, map_id: str) -> None:
        """Drop a map's rows from maps, scans, proposals and jobs."""
        self.delete_maps([map_id])

    def delete_maps(self, map_ids: list[str]) -> None:
        """Drop the rows of many maps in one transaction."""
        with self._lock:
            try:
                for table, col in _TABLES:
                    sql = f"DELETE FROM {table} WHERE {col}=?"  # noqa: S608 - constant names
                    self._db.executemany(sql, [(i,) for i in map_ids])
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise
