"""Library listing helpers: query validation, item shaping and cover lookup."""

from dataclasses import dataclass
from pathlib import Path

from saber_tooth.mapio import MapParseError
from saber_tooth.mapio.discover import _entries_v2, _entries_v4, _opt_name, _read_json, find_info
from saber_tooth.store_maps import SORT_KEYS, STATUS_FILTERS

MAX_LIMIT = 100
MAX_QUERY = 200
MAX_COVER_BYTES = 5 * 1024 * 1024
COVER_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
ITEM_FIELDS = ("id", "folder", "title", "mapper", "environment", "parse_error", "scanned_at")
_CACHE_SIZE = 4096


@dataclass(frozen=True)
class MapQuery:
    offset: int = 0
    limit: int = 40
    sort: str = "title"
    order: str = "asc"
    q: str = ""
    status: str = "all"


def parse_query(params: dict[str, str], max_limit: int = MAX_LIMIT) -> MapQuery:
    """Validate raw query-string values; raise ValueError with a client-safe message."""
    offset = _int(params.get("offset", "0"), "offset", 0, 10**9)
    limit = _int(params.get("limit", "40"), "limit", 1, max_limit)
    sort = params.get("sort", "title")
    order = params.get("order", "asc")
    status = params.get("status", "all")
    q = params.get("q", "")
    if sort not in SORT_KEYS:
        raise ValueError(f"sort must be one of {', '.join(SORT_KEYS)}")
    if order not in ("asc", "desc"):
        raise ValueError("order must be asc or desc")
    if status not in STATUS_FILTERS:
        raise ValueError(f"status must be one of {', '.join(sorted(STATUS_FILTERS))}")
    if len(q) > MAX_QUERY:
        raise ValueError(f"q is longer than {MAX_QUERY} characters")
    return MapQuery(offset, limit, sort, order, q, status)


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


def _read_extras(folder: Path) -> tuple[str, list[str]]:
    info = _read_json(find_info(folder))
    v4 = str(info.get("version", "")).startswith("4.")
    entries = _entries_v4(info) if v4 else _entries_v2(info)
    key = "coverImageFilename" if v4 else "_coverImageFilename"
    return _opt_name(info.get(key, "")), [str(e["name"]) for e in entries]


class Extras:
    """Cover filename and difficulty names per folder, cached until Info.dat changes."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[tuple[int, int], tuple[str, list[str]]]] = {}

    def get(self, folder: Path) -> tuple[str, list[str]]:
        try:
            st = find_info(folder).stat()
            stamp = (st.st_mtime_ns, st.st_size)
        except (MapParseError, OSError):
            return "", []
        hit = self._cache.get(str(folder))
        if hit and hit[0] == stamp:
            return hit[1]
        try:
            value = _read_extras(folder)
        except (MapParseError, OSError, KeyError, TypeError, ValueError):
            value = ("", [])
        if len(self._cache) >= _CACHE_SIZE:
            self._cache.clear()
        self._cache[str(folder)] = (stamp, value)
        return value


def shape_item(row: dict, levels: Path, extras: Extras) -> dict:
    item = {k: row[k] for k in ITEM_FIELDS}
    item.update(errors=row["errors"], warnings=row["warnings"], status=row["status"])
    item.update(approved=row["approved"], pending=row["pending"])
    item.update(cover_url=None, difficulties=[])
    folder = folder_path(levels, row["folder"])
    if folder is not None and not row["parse_error"]:
        cover, difficulties = extras.get(folder)
        item["difficulties"] = difficulties
        if cover_path(folder, cover) is not None:
            item["cover_url"] = f"/api/maps/{row['id']}/cover"
    return item
