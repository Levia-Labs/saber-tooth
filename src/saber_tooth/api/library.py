"""Library listing helpers: query validation, item shaping and cover lookup."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from saber_tooth.mapio import MapParseError
from saber_tooth.mapio.discover import _entries_v2, _entries_v4, _opt_name, _read_json, find_info
from saber_tooth.store_maps import (
    LEVEL_MODES,
    LEVEL_NAMES,
    MAX_ENVS,
    MAX_MAPPERS,
    Q_FIELDS,
    RANGE_LIMITS,
    RANGES,
    SORT_KEYS,
    STATUS_FILTERS,
)

MAX_LIMIT = 100
MAX_QUERY = 200
MAX_COVER_BYTES = 5 * 1024 * 1024
COVER_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
AUDIO_TYPES = {".egg": "audio/ogg", ".ogg": "audio/ogg", ".wav": "audio/wav", ".mp3": "audio/mpeg"}
ITEM_FIELDS = (
    "id", "folder", "title", "mapper", "environment", "parse_error", "scanned_at", "bpm",
)  # fmt: skip
MAX_ENV_LEN = 200
MAX_MAPPER_LEN = 200
MAPPER_SEP = ""  # joins repeated mapper values; names may contain commas
_CACHE_SIZE = 4096


@dataclass(frozen=True)
class MapQuery:
    offset: int = 0
    limit: int = 40
    sort: str = "title"
    order: str = "asc"
    q: str = ""
    status: tuple[str, ...] = ()
    env: tuple[str, ...] = ()
    q_fields: str = "all"
    mapper: tuple[str, ...] = ()
    level: tuple[str, ...] = ()
    level_mode: str = "any"
    duration_min: float | None = None
    duration_max: float | None = None
    bpm_min: float | None = None
    bpm_max: float | None = None


def _split(raw: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(p.strip() for p in raw.split(",") if p.strip()))


def parse_query(params: dict[str, str], max_limit: int = MAX_LIMIT) -> MapQuery:
    """Validate raw query-string values; raise ValueError with a client-safe message."""
    offset = _int(params.get("offset", "0"), "offset", 0, 10**9)
    limit = _int(params.get("limit", "40"), "limit", 1, max_limit)
    sort = params.get("sort", "title")
    order = params.get("order", "asc")
    statuses = _split(params.get("status", "all"))
    envs = _split(params.get("env", ""))
    fields = _split(params.get("q_fields", ""))
    mappers = tuple(dict.fromkeys(m for m in params.get("mapper", "").split(MAPPER_SEP) if m))
    levels = _split(params.get("level", ""))
    level_mode = params.get("level_mode", "any")
    q = params.get("q", "")
    ranges = {name: _number(params.get(name), name) for name, _, _ in RANGES}
    if sort not in SORT_KEYS:
        raise ValueError(f"sort must be one of {', '.join(SORT_KEYS)}")
    if order not in ("asc", "desc"):
        raise ValueError("order must be asc or desc")
    if not set(statuses) <= STATUS_FILTERS:
        raise ValueError(f"status must be one of {', '.join(sorted(STATUS_FILTERS))}")
    if len(envs) > MAX_ENVS or any(len(e) > MAX_ENV_LEN for e in envs):
        raise ValueError(f"env takes at most {MAX_ENVS} names of {MAX_ENV_LEN} characters")
    if not set(fields) <= Q_FIELDS:
        raise ValueError(f"q_fields must be a list of {', '.join(sorted(Q_FIELDS))}")
    if len(mappers) > MAX_MAPPERS or any(len(m) > MAX_MAPPER_LEN for m in mappers):
        raise ValueError(f"mapper takes at most {MAX_MAPPERS} names of {MAX_MAPPER_LEN} characters")
    if not set(levels) <= set(LEVEL_NAMES):
        raise ValueError(f"level must be one of {', '.join(LEVEL_NAMES)}")
    if level_mode not in LEVEL_MODES:
        raise ValueError("level_mode must be any or all")
    if len(q) > MAX_QUERY:
        raise ValueError(f"q is longer than {MAX_QUERY} characters")
    for dim in RANGE_LIMITS:
        low, high = ranges[f"{dim}_min"], ranges[f"{dim}_max"]
        if low is not None and high is not None and low > high:
            raise ValueError(f"{dim}_min must not exceed {dim}_max")
    status = () if "all" in statuses else statuses
    scope = "name" if len(fields) > 1 else fields[0] if fields else "all"
    return MapQuery(
        offset, limit, sort, order, q, status, envs, scope, mappers, levels, level_mode, **ranges
    )


def _number(raw: str | None, name: str) -> float | None:
    """A finite number within the range limits, or None when the parameter is absent or empty."""
    if raw is None or raw.strip() == "":
        return None
    low, high = RANGE_LIMITS[name.split("_")[0]]
    try:
        value = float(raw) if raw.isascii() and len(raw) <= 20 else float("nan")
    except ValueError:
        value = float("nan")
    if not low <= value <= high:
        raise ValueError(f"{name} must be a number from {low:g} to {high:g}")
    return value


def _int(raw: str, name: str, low: int, high: int) -> int:
    if not raw.isascii() or not raw.isdigit() or len(raw) > 12 or not low <= int(raw) <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    return int(raw)


def folder_path(levels: Path, name: str) -> Path | None:
    """The map folder under levels, or None when the stored name is not a plain real folder."""
    folder = levels / name
    if Path(name).name != name or name in ("", ".", "..") or folder.is_symlink():
        return None
    return folder if folder.is_dir() else None


def cover_path(folder: Path, cover_file: str) -> Path | None:
    """The cover image inside folder, or None; never a path outside it, never oversized."""
    suffix = Path(cover_file).suffix.lower()
    if not cover_file or suffix not in COVER_TYPES or Path(cover_file).name != cover_file:
        return None
    if any(c in cover_file for c in "/\\:\x00"):
        return None
    try:
        root = folder.resolve()
        found = next((p for p in folder.iterdir() if p.name.lower() == cover_file.lower()), None)
        if found is None or found.is_symlink() or found.resolve().parent != root:
            return None
        if not found.is_file() or found.stat().st_size > MAX_COVER_BYTES:
            return None
    except OSError:
        return None
    return found


class Extra(NamedTuple):
    cover: str
    difficulties: list[str]
    song: str
    preview_start: float | None


def _preview(raw: object) -> float | None:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    return float(raw) if math.isfinite(raw) and raw >= 0 else None


def _read_extras(folder: Path) -> Extra:
    info = _read_json(find_info(folder))
    v4 = str(info.get("version", "")).startswith("4.")
    entries = _entries_v4(info) if v4 else _entries_v2(info)
    key = "coverImageFilename" if v4 else "_coverImageFilename"
    audio = info.get("audio") if v4 else info
    audio = audio if isinstance(audio, dict) else {}
    song_key = "songFilename" if v4 else "_songFilename"
    start_key = "previewStartTime" if v4 else "_previewStartTime"
    try:
        song = _opt_name(audio.get(song_key, ""))
    except MapParseError:
        song = ""
    names = [str(e["name"]) for e in entries]
    return Extra(_opt_name(info.get(key, "")), names, song, _preview(audio.get(start_key)))


def audio_path(folder: Path, song_file: str) -> Path | None:
    """The song file inside folder, or None; never a path outside it or of another type."""
    if not song_file or Path(song_file).suffix.lower() not in AUDIO_TYPES:
        return None
    if Path(song_file).name != song_file or any(c in song_file for c in "/\\:\x00"):
        return None
    try:
        root = folder.resolve()
        found = next((p for p in folder.iterdir() if p.name.lower() == song_file.lower()), None)
        if found is None or found.is_symlink() or found.resolve().parent != root:
            return None
        return found if found.is_file() else None
    except OSError:
        return None


class Extras:
    """Cover, difficulties and song per folder, cached until Info.dat changes."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[tuple[int, int], Extra]] = {}
        self._media: dict[str, tuple[tuple[int, int, int], bool, bool]] = {}

    def media(self, folder: Path, extra: Extra) -> tuple[bool, bool]:
        """Whether the folder has a usable cover and song, cached until its listing changes."""
        try:
            stamp = (folder.stat().st_mtime_ns, *self._stamp(folder))
        except (MapParseError, OSError):
            stamp = None
        hit = self._media.get(str(folder))
        if stamp is not None and hit and hit[0] == stamp:
            return hit[1], hit[2]
        cover = cover_path(folder, extra.cover) is not None
        audio = audio_path(folder, extra.song) is not None
        if stamp is not None:
            if len(self._media) >= _CACHE_SIZE:
                self._media.clear()
            self._media[str(folder)] = (stamp, cover, audio)
        return cover, audio

    @staticmethod
    def _stamp(folder: Path) -> tuple[int, int]:
        st = find_info(folder).stat()
        return st.st_mtime_ns, st.st_size

    def get(self, folder: Path) -> Extra:
        empty = Extra("", [], "", None)
        try:
            stamp = self._stamp(folder)
        except (MapParseError, OSError):
            return empty
        hit = self._cache.get(str(folder))
        if hit and hit[0] == stamp:
            return hit[1]
        try:
            value = _read_extras(folder)
        except (MapParseError, OSError, KeyError, TypeError, ValueError):
            value = empty
        if len(self._cache) >= _CACHE_SIZE:
            self._cache.clear()
        self._cache[str(folder)] = (stamp, value)
        return value


def shape_item(row: dict, levels: Path, extras: Extras) -> dict:
    item = {k: row[k] for k in ITEM_FIELDS}
    item.update(errors=row["errors"], warnings=row["warnings"], status=row["status"])
    item.update(approved=row["approved"], pending=row["pending"])
    item["duration_s"] = row["duration_s"]
    item.update(fixed_copy_id=row["fixed_copy_id"], fixed_copy_folder=row["fixed_copy_folder"])
    item.update(original_id=row["original_id"], original_folder=row["original_folder"])
    job = {
        "id": row["job_id"],
        "kind": row["job_kind"],
        "status": row["job_status"],
        "position": row["job_position"],
        "progress": row["job_progress"],
    }
    item["job"] = job if row["job_id"] else None
    item.update(cover_url=None, difficulties=[], audio_url=None, preview_start=None)
    folder = folder_path(levels, row["folder"])
    if folder is not None and not row["parse_error"]:
        extra = extras.get(folder)
        item["difficulties"] = extra.difficulties
        has_cover, has_audio = extras.media(folder, extra)
        if has_cover:
            item["cover_url"] = f"/api/maps/{row['id']}/cover"
        if has_audio:
            item["audio_url"] = f"/api/maps/{row['id']}/audio"
            item["preview_start"] = extra.preview_start
    return item
