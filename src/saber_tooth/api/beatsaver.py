"""BeatSaver route logic: search, map and playlist lookups, downloads, presets, export."""

import math
import re
from pathlib import Path
from typing import Any

from saber_tooth.api.core import Api, ApiError
from saber_tooth.beatsaver.cache import BsCache
from saber_tooth.beatsaver.client import BeatSaverClient, BeatSaverError, download_url_ok
from saber_tooth.beatsaver.download import install
from saber_tooth.beatsaver.models import BsMap, BsPlaylist
from saber_tooth.beatsaver.params import parse_search
from saber_tooth.beatsaver.playlist_query import parse_playlist_query
from saber_tooth.beatsaver.playlists import PlaylistsDisabled, export_bplist
from saber_tooth.beatsaver.presets import PresetConflict, PresetError, Presets
from saber_tooth.beatsaver.search import SearchResult, search
from saber_tooth.safe_fs import LevelsWriter

MAX_DOWNLOAD = 100
DOWNLOAD_DEADLINE = 600.0
RATE_SKIP = "skipped: BeatSaver rate limit, try again later"
MAX_EXPORT = 500
BS_ID = re.compile(r"[0-9a-fA-F]{1,12}")
PLAYLIST_ID = re.compile(r"[0-9]{1,9}")
KEY_PREFIX = re.compile(r"([0-9a-fA-F]{1,12}) \(")
MAX_META = 200
PLAYLIST_SCAN_PAGES = 5
PLAYLIST_WANTED = 20


class BsHttpError(ApiError):
    """A BeatSaver failure with an optional retry hint in seconds."""

    def __init__(self, status: int, message: str, retry_after: int | None = None) -> None:
        super().__init__(status, message)
        self.retry_after = retry_after


def bs_error(exc: BeatSaverError) -> BsHttpError:
    text = str(exc)
    if text.startswith("not found"):
        return BsHttpError(404, text)
    if exc.retry_after is not None and "rate limited" in text:
        return BsHttpError(429, text, math.ceil(exc.retry_after))
    return BsHttpError(502, text)


def _url(value: str) -> str | None:
    return value if download_url_ok(value) else None


def playlist_view(p: BsPlaylist) -> dict:
    return {
        "id": str(p.id), "name": p.name, "owner": p.owner,
        "cover_url": _url(p.cover_url), "map_count": p.maps_count,
        "mapper_count": p.mapper_count, "duration": p.duration,
        "upvotes": p.upvotes, "downvotes": p.downvotes, "rating": p.rating,
        "min_nps": p.min_nps, "max_nps": p.max_nps,
        "created_at": p.created_at, "curated": p.curated,
    }  # fmt: skip


class _PlaylistSource:
    """Adapts one playlist to the `search(params, page)` shape the cursor search expects."""

    def __init__(self, client: BeatSaverClient, pid: int, meta: dict[int, BsPlaylist]) -> None:
        self.client, self.pid, self.meta = client, pid, meta

    def search(self, params: dict[str, str], page: int) -> list[BsMap]:
        playlist, maps = self.client.playlist_page_full(self.pid, page)
        if playlist.name:
            if len(self.meta) >= MAX_META:
                self.meta.clear()
            self.meta[self.pid] = playlist
        return maps


class BeatSaverApi:
    def __init__(
        self, api: Api, client: BeatSaverClient, playlists_dir: Path | None = None
    ) -> None:
        self.api, self.service, self.client = api, api.service, client
        db = self.service.data / "beatsaver.db"
        self.cache, self.presets = BsCache(db), Presets(db)
        self.playlists_dir = Path(playlists_dir) if playlists_dir else None
        self._meta: dict[int, BsPlaylist] = {}
        api.jobs.register("bs-download", lambda a, p: self._download_job(a["ids"]))

    # views ---------------------------------------------------------------------

    def _installed(self) -> tuple[dict[str, str], dict[str, str]]:
        self.service.refresh_if_changed()
        by_key: dict[str, str] = {}
        by_hash: dict[str, str] = {}
        for row in self.service.store.bs_rows():
            if row["bs_id"]:
                by_key[row["bs_id"].lower()] = row["id"]
            if row["bs_hash"]:
                by_hash[row["bs_hash"].lower()] = row["id"]
            found = KEY_PREFIX.match(row["folder"])
            if found:
                by_key.setdefault(found.group(1).lower(), row["id"])
        return by_key, by_hash

    def view(self, m: BsMap, index: tuple[dict[str, str], dict[str, str]]) -> dict:
        by_key, by_hash = index
        library_id = by_key.get(m.id.lower()) or (by_hash.get(m.hash) if m.hash else None)
        return {
            "id": m.id, "name": m.name, "song": m.song_name, "mapper": m.mapper,
            "cover_url": _url(m.cover_url), "preview_url": _url(m.preview_url),
            "bpm": m.bpm, "duration": m.duration, "rating": m.score,
            "upvotes": m.upvotes, "downvotes": m.downvotes, "tags": list(m.tags),
            "ranked": m.ranked,
            "difficulties": [
                {"difficulty": d.difficulty, "nps": d.nps, "njs": d.njs}
                for d in m.diffs if d.characteristic == "Standard"
            ],
            "installed": library_id is not None, "library_id": library_id,
        }  # fmt: skip

    def _page(self, res: SearchResult) -> dict:
        index = self._installed()
        out: dict[str, Any] = {
            "items": [self.view(m, index) for m in res.items],
            "cursor": res.cursor,
            "scanned": res.scanned,
            "matched": res.matched,
        }
        if res.partial_reason:
            out["partial"] = True
            out["retry_after"] = math.ceil(res.retry_after) if res.retry_after else None
        return out

    @staticmethod
    def _parse(params: dict[str, str], max_limit: int = 100):
        try:
            return parse_search(params, max_limit)
        except ValueError as exc:
            raise ApiError(400, str(exc)) from None

    # routes --------------------------------------------------------------------

    def search(self, params: dict[str, str], max_limit: int = 100) -> dict:
        sp = self._parse(params, max_limit)
        try:
            res = search(self.client, self.cache, sp.server, sp.local, sp.cursor, sp.limit)
        except BeatSaverError as exc:
            raise bs_error(exc) from None
        return self._page(res)

    def map(self, raw: str) -> dict:
        if not BS_ID.fullmatch(raw):
            raise ApiError(404, f"unknown BeatSaver map: {raw}")
        found = self._resolve([raw.lower()])[0]
        if not found:
            raise ApiError(404, f"unknown BeatSaver map: {raw}")
        return self.view(next(iter(found.values())), self._installed())

    def playlists_search(self, params: dict[str, str]) -> dict:
        try:
            pq = parse_playlist_query(params)
        except ValueError as exc:
            raise ApiError(400, str(exc)) from None
        page, items = pq.cursor, []
        try:
            for _ in range(PLAYLIST_SCAN_PAGES):
                raw, docs = self.client.playlist_search_page(pq.server, page)
                page += 1
                items += [p for p in docs if pq.local.matches(p)]
                if not raw or len(items) >= PLAYLIST_WANTED:
                    break
        except BeatSaverError as exc:
            raise bs_error(exc) from None
        return {"items": [playlist_view(p) for p in items], "cursor": str(page) if raw else None}

    def playlist(self, raw: str, params: dict[str, str]) -> dict:
        if not PLAYLIST_ID.fullmatch(raw):
            raise ApiError(404, f"unknown BeatSaver playlist: {raw}")
        pid, sp = int(raw), self._parse(params)
        source = _PlaylistSource(self.client, pid, self._meta)
        try:
            res = search(source, self.cache, sp.server, sp.local, sp.cursor, sp.limit, scope=raw)  # type: ignore[arg-type]
            if pid not in self._meta:
                self._meta[pid] = self.client.playlist_page_full(pid, 0)[0]
        except BeatSaverError as exc:
            raise bs_error(exc) from None
        out = self._page(res)
        out["playlist"] = playlist_view(self._meta.get(pid) or BsPlaylist(pid, "", "", 0, 0, 0, ""))
        return out

    # downloads -----------------------------------------------------------------

    @staticmethod
    def _ids(body: object, limit: int) -> list[str]:
        raw = body.get("ids") if isinstance(body, dict) else None
        if not isinstance(raw, list) or not raw:
            raise ApiError(400, 'send {"ids": [BeatSaver keys]}')
        if len(raw) > limit:
            raise ApiError(413, f"at most {limit} ids per request")
        if not all(isinstance(i, str) and BS_ID.fullmatch(i) for i in raw):
            raise ApiError(400, "ids must be BeatSaver keys")
        return list(dict.fromkeys(i.lower() for i in raw))

    def _resolve(self, ids: list[str]) -> tuple[dict[str, BsMap], dict[str, str]]:
        """Map details by id (cache first) and a failure reason for every id not found."""
        found = self.cache.get_maps(ids)
        missing = [i for i in ids if i not in found]
        reasons: dict[str, str] = {}
        if missing:
            try:
                fetched = self.client.maps_by_ids(missing)
                self.cache.put_maps(fetched)
                found.update({m.id.lower(): m for m in fetched})
            except BeatSaverError as exc:
                reasons = dict.fromkeys(missing, str(exc))
        return found, reasons

    def download(self, body: object) -> dict:
        ids = self._ids(body, MAX_DOWNLOAD)
        return {"job": self.api.jobs.submit("bs-download", {"ids": ids})}

    def _download_job(self, ids: list[str]) -> dict:
        found, reasons = self._resolve(ids)
        tmp = self.service.data / "bs-tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        writer = LevelsWriter(self.service.levels)
        results = []
        deadline = self.client.deadline_in(DOWNLOAD_DEADLINE)
        limited = False
        for i in ids:
            if limited:
                results.append({"id": i, "status": "skipped", "reason": RATE_SKIP, "folder": None})
                continue
            bs = found.get(i)
            if bs is None:
                results.append({
                    "id": i, "status": "failed",
                    "reason": reasons.get(i, "not found on BeatSaver"), "folder": None,
                })  # fmt: skip
                continue
            try:
                out = install(self.client, writer, self.service.store, bs, tmp, deadline)
                limited = out.rate_limited
                row = {"status": out.status, "reason": out.reason, "folder": out.folder}
            except Exception as exc:  # one map must never abort the batch
                row = {"status": "failed", "reason": type(exc).__name__, "folder": None}
            results.append({"id": i, **row})
        self.service.refresh_if_changed()
        return {"results": results}

    def export(self, body: object) -> dict:
        if not self.playlists_enabled():
            raise ApiError(404, "playlist export is not enabled")
        title = body.get("title") if isinstance(body, dict) else None
        if not isinstance(title, str) or not title.strip() or len(title) > 120:
            raise ApiError(400, "title must be 1 to 120 characters")
        ids = self._ids(body, MAX_EXPORT)
        found, reasons = self._resolve(ids)
        if reasons:
            raise ApiError(502, next(iter(reasons.values())))
        maps = [found[i] for i in ids if i in found]
        try:
            return {"path": str(export_bplist(title, maps, self.playlists_dir))}
        except (PlaylistsDisabled, OSError) as exc:
            raise ApiError(409, str(exc)) from None

    def playlists_enabled(self) -> bool:
        return self.playlists_dir is not None and self.playlists_dir.is_dir()

    def config(self) -> dict:
        return {"playlists_enabled": self.playlists_enabled()}

    # presets -------------------------------------------------------------------

    def preset_add(self, body: object) -> dict:
        if not isinstance(body, dict):
            raise ApiError(400, 'send {"name", "filters"}')
        try:
            return self.presets.add(body.get("name"), body.get("filters"))
        except PresetConflict as exc:
            raise ApiError(409, str(exc)) from None
        except PresetError as exc:
            raise ApiError(400, str(exc)) from None

    def preset_delete(self, raw: str) -> dict:
        if not raw.isascii() or not raw.isdigit() or len(raw) > 12:
            raise ApiError(404, f"unknown preset: {raw}")
        if not self.presets.delete(int(raw)):
            raise ApiError(404, f"unknown preset: {raw}")
        return {"deleted": int(raw)}
