"""Saved filter presets in SQLite; the "Easy-to-Hard gems" preset is seeded once."""

import json
import sqlite3
import threading
from pathlib import Path

from saber_tooth.beatsaver.params import FILTER_KEYS, parse_filters

MAX_PRESETS = 100
MAX_NAME = 80
SEEDED_NAME = "Easy-to-Hard gems"
OLD_SEEDED_NAME = "Gentle full-spread hits"
SEEDED_FILTERS = {
    "diffs": "Easy,Normal,Hard",
    "diffs_mode": "all",
    "min_rating": "0.95",
    "nps_min": "1",
    "nps_max": "2",
    "nps_scope": "any",
    "tags": "electronic,dubstep,rock,metal,punk,j-rock,techno,house,trance,drum-and-bass",
    "order": "Rating",
    "ascending": "false",
}
_SCHEMA = """
CREATE TABLE IF NOT EXISTS bs_presets(
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, filters TEXT, seeded INTEGER);
CREATE TABLE IF NOT EXISTS bs_meta(key TEXT PRIMARY KEY, value TEXT);
"""


class PresetError(ValueError):
    """The preset name or filters are invalid."""


class PresetConflict(PresetError):
    """A preset with this name exists, or the limit is reached."""


def _row(r: sqlite3.Row | tuple) -> dict:
    return {"id": r[0], "name": r[1], "filters": json.loads(r[2]), "seeded": bool(r[3])}


class Presets:
    def __init__(self, db_path: Path) -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False, timeout=15)
        with self._lock:
            self._db.executescript(_SCHEMA)
            done = self._db.execute("SELECT 1 FROM bs_meta WHERE key='seeded'").fetchone()
            if not done:
                self._db.execute(
                    "INSERT OR IGNORE INTO bs_presets(name, filters, seeded) VALUES(?,?,1)",
                    (SEEDED_NAME, json.dumps(SEEDED_FILTERS)),
                )
                self._db.execute("INSERT INTO bs_meta(key, value) VALUES('seeded', '1')")
            self._db.execute(
                "UPDATE bs_presets SET name=? WHERE name=? AND seeded=1 AND NOT EXISTS "
                "(SELECT 1 FROM bs_presets WHERE name=?)",
                (SEEDED_NAME, OLD_SEEDED_NAME, SEEDED_NAME),
            )
            self._db.commit()

    def list(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT id, name, filters, seeded FROM bs_presets ORDER BY seeded DESC, id"
            ).fetchall()
        return [_row(r) for r in rows]

    def add(self, name: object, filters: object) -> dict:
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > MAX_NAME:
            raise PresetError(f"name must be 1 to {MAX_NAME} characters")
        if not isinstance(filters, dict) or not set(filters) <= FILTER_KEYS:
            raise PresetError("filters must be an object of known filter keys")
        if not all(isinstance(v, str) and len(v) <= 500 for v in filters.values()):
            raise PresetError("filter values must be short strings")
        try:
            parse_filters(filters)
        except ValueError as exc:
            raise PresetError(str(exc)) from None
        name = name.strip()
        with self._lock:
            count = self._db.execute("SELECT count(*) FROM bs_presets").fetchone()[0]
            if count >= MAX_PRESETS:
                raise PresetConflict("too many presets")
            try:
                cur = self._db.execute(
                    "INSERT INTO bs_presets(name, filters, seeded) VALUES(?,?,0)",
                    (name, json.dumps(filters)),
                )
            except sqlite3.IntegrityError:
                raise PresetConflict("a preset with this name exists") from None
            self._db.commit()
            return _row((cur.lastrowid, name, json.dumps(filters), 0))

    def delete(self, preset_id: int) -> bool:
        with self._lock:
            cur = self._db.execute("DELETE FROM bs_presets WHERE id=?", (preset_id,))
            self._db.commit()
            return cur.rowcount > 0
