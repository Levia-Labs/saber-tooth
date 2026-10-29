"""Local playlists as JSON files (plus an optional cover image) under one data folder."""

import json
import os
import re
import tempfile
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

PLAYLIST_ID = re.compile(r"[0-9a-f]{32}")
MAP_ID = re.compile(r"[0-9a-f]{12}")
HASH = re.compile(r"[0-9A-Fa-f]{40}")
MAX_SONGS = 2000
MAX_COVER = 2 * 1024 * 1024


class PlaylistError(ValueError):
    """Invalid playlist input."""


def _text(raw: object, name: str, limit: int, required: bool = False) -> str:
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raise PlaylistError(f"{name} must be text")
    out = raw.strip()[:limit] if name == "description" else " ".join(raw.split())[:limit]
    if required and not out:
        raise PlaylistError(f"{name} is required")
    return out


def clean_song(raw: object) -> dict:
    """One stored song: a library map (map_id) or a hash-only entry (BeatSaver)."""
    if not isinstance(raw, dict):
        raise PlaylistError("each song must be an object")
    song: dict = {
        "song_name": _text(raw.get("song_name"), "song_name", 200),
        "mapper": _text(raw.get("mapper"), "mapper", 200),
    }
    mid, h, key = raw.get("map_id"), raw.get("hash"), raw.get("key")
    if mid is not None:
        if not isinstance(mid, str) or not MAP_ID.fullmatch(mid):
            raise PlaylistError("invalid map_id")
        song["map_id"] = mid
    if h is not None:
        if not isinstance(h, str) or not HASH.fullmatch(h):
            raise PlaylistError("hash must be 40 hex digits")
        song["hash"] = h.upper()
    if "map_id" not in song and "hash" not in song:
        raise PlaylistError("each song needs a map_id or a hash")
    if key is not None:
        song["key"] = _text(key, "key", 16)
    return song


def clean_record(payload: object) -> dict:
    """The editable fields of a playlist from a request body."""
    if not isinstance(payload, dict):
        raise PlaylistError("send a JSON object")
    songs = payload.get("songs", [])
    if not isinstance(songs, list) or len(songs) > MAX_SONGS:
        raise PlaylistError(f"songs must be a list of at most {MAX_SONGS}")
    out: dict = {
        "title": _text(payload.get("title"), "title", 120, required=True),
        "author": _text(payload.get("author"), "author", 120),
        "description": _text(payload.get("description"), "description", 2000),
        "folder": _text(payload.get("folder"), "folder", 120),
        "sync": bool(payload.get("sync", False)),
        "songs": [],
    }
    seen: set[tuple] = set()
    for s in songs:
        song = clean_song(s)
        ident = (song.get("map_id"), song.get("hash"))
        if ident not in seen:
            seen.add(ident)
            out["songs"].append(song)
    return out


def _atomic(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class PlaylistStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._lock = threading.Lock()

    def _json(self, pid: str) -> Path:
        return self.root / f"{pid}.json"

    def _cover(self, pid: str) -> Path:
        return self.root / f"{pid}.cover"

    def list(self) -> list[dict]:
        try:
            files = sorted(self.root.glob("*.json"))
        except OSError:
            return []
        recs = (self.get(p.stem) for p in files if PLAYLIST_ID.fullmatch(p.stem))
        return [r for r in recs if r]

    def get(self, pid: str) -> dict | None:
        if not PLAYLIST_ID.fullmatch(pid):
            return None
        try:
            rec = json.loads(self._json(pid).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return rec if isinstance(rec, dict) else None

    def save(
        self,
        fields: dict,
        pid: str | None = None,
        cover: bytes | None = None,
        clear_cover: bool = False,
    ) -> dict:
        """Create (pid None) or update a playlist; `cover` replaces the image."""
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            now = datetime.now(UTC).isoformat()
            old = self.get(pid) if pid else None
            if pid and old is None:
                raise KeyError(pid)
            base = old or {"id": uuid.uuid4().hex, "created_at": now, "exported": ""}
            rec = {**base, **fields, "updated_at": now}
            _atomic(self._json(rec["id"]), json.dumps(rec, indent=2).encode("utf-8"))
            if cover is not None:
                _atomic(self._cover(rec["id"]), cover)
            elif clear_cover:
                self._cover(rec["id"]).unlink(missing_ok=True)
            return rec

    def cover(self, pid: str) -> bytes | None:
        if not PLAYLIST_ID.fullmatch(pid):
            return None
        try:
            return self._cover(pid).read_bytes()
        except OSError:
            return None

    def delete(self, pid: str) -> bool:
        if self.get(pid) is None:
            return False
        with self._lock:
            self._json(pid).unlink(missing_ok=True)
            self._cover(pid).unlink(missing_ok=True)
        return True
