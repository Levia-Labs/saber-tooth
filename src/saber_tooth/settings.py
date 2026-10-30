"""User settings kept in a small SQLite file next to the main store.

A separate file keeps the settings table clear of the jobs table's write traffic. Values are
read through a cache, so the job worker can ask for the concurrency cap on every pass.
"""

import sqlite3
import threading
from pathlib import Path, PurePosixPath, PureWindowsPath

DEFAULT_JOBS = 1
MAX_PATH_CHARS = 1024
GAME_MARKERS = ("Beat Saber_Data", "Beat Saber.exe", "BeatSaberVersion.txt")


class SettingError(ValueError):
    """A submitted setting is out of range or unusable; the message is shown to the user."""


def clean_game_dir(raw: object) -> Path | None:
    """The resolved Beat Saber install folder for a submitted path; None for an empty value."""
    if raw == "":
        return None
    if not isinstance(raw, str) or "\x00" in raw or len(raw) > MAX_PATH_CHARS:
        raise SettingError("the game folder must be a path")
    if not (PurePosixPath(raw).is_absolute() or PureWindowsPath(raw).is_absolute()):
        raise SettingError("the game folder must be an absolute path")
    try:
        path = Path(raw).resolve()
        is_dir = path.is_dir()
    except (OSError, ValueError):
        is_dir = False
    if not is_dir:
        raise SettingError(f"not a folder: {raw}")
    if not any((path / marker).exists() for marker in GAME_MARKERS):
        raise SettingError("that folder is not a Beat Saber install (no Beat Saber_Data inside)")
    return path


class Settings:
    def __init__(self, path: Path) -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")
        self._db.commit()
        self._cache: dict[str, str] = {
            k: v for k, v in self._db.execute("SELECT key, value FROM settings")
        }

    def get(self, key: str, default: str | None = None) -> str | None:
        with self._lock:
            return self._cache.get(key, default)

    def put(self, key: str, value: str | None) -> None:
        with self._lock:
            if value is None:
                self._db.execute("DELETE FROM settings WHERE key=?", (key,))
                self._cache.pop(key, None)
            else:
                self._db.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?)"
                    " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
                self._cache[key] = value
            self._db.commit()

    def max_concurrent_jobs(self) -> int:
        raw = self.get("max_concurrent_jobs")
        return int(raw) if raw and raw.isdigit() and int(raw) >= 1 else DEFAULT_JOBS

    def set_max_concurrent_jobs(self, value: object, recommended: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise SettingError("max_concurrent_jobs must be a whole number")
        if not 1 <= value <= max(1, recommended):
            raise SettingError(f"max_concurrent_jobs must be between 1 and {max(1, recommended)}")
        self.put("max_concurrent_jobs", str(value))
        return value

    def game_dir(self) -> Path | None:
        raw = self.get("game_dir")
        return Path(raw) if raw else None

    def set_game_dir(self, raw: object) -> Path | None:
        path = clean_game_dir(raw)
        self.put("game_dir", None if path is None else str(path))
        return path
