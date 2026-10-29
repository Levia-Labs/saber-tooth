"""Local playlist logic: CRUD, build from library maps or job output, export, live .bplist."""

import base64
import binascii
import os
from pathlib import Path

from saber_tooth.api.core import JOB_ID, MAP_ID, Api, ApiError
from saber_tooth.api.library import MAX_COVER_BYTES, shape_item
from saber_tooth.api.web_routes import read_cover
from saber_tooth.beatsaver.playlists import (
    BadSubfolder,
    PlaylistsDisabled,
    build_doc,
    write_bplist,
)
from saber_tooth.playlists.resolve import Library, resolve_all, to_doc
from saber_tooth.playlists.store import (
    MAX_COVER,
    PLAYLIST_ID,
    PlaylistError,
    PlaylistStore,
    clean_record,
    clean_song,
)
from saber_tooth.store_maps import FIXED_COPY_SUFFIX

LIVE = {"latest-generated": "Latest generated", "latest-fixed": "Latest fixed"}
LIVE_LIMIT = 20
PNG, JPEG = b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff"


def image_type(data: bytes) -> str | None:
    if data.startswith(PNG):
        return "image/png"
    return "image/jpeg" if data.startswith(JPEG) else None


class PlaylistsApi:
    def __init__(self, api: Api, export_dir: Path | None, root: Path | None = None) -> None:
        self.api = api
        self.export_dir = export_dir
        self.store = PlaylistStore(root or api.service.data / "playlists")

    # helpers -------------------------------------------------------------------

    def _lib(self) -> Library:
        self.api.service.refresh_if_changed()
        return Library(self.api.store.list_maps(), self.api.service.levels)

    def _rec(self, pid: str) -> dict:
        rec = self.store.get(pid)
        if rec is None:
            raise ApiError(404, f"unknown playlist: {pid}")
        return rec

    @staticmethod
    def _base(base: str) -> str:
        return (os.environ.get("SABER_PUBLIC_URL") or base).rstrip("/")

    def config(self) -> dict:
        ok = self.export_dir is not None and self.export_dir.is_dir()
        return {"export_enabled": ok, "live": LIVE}

    def _cover_from(self, spec: object) -> tuple[bytes | None, bool]:
        """(bytes, clear) for a request's `cover`: {map_id} | {data: base64} | {clear: true}."""
        if spec is None:
            return None, False
        if not isinstance(spec, dict):
            raise ApiError(400, "cover must be an object")
        if spec.get("clear"):
            return None, True
        if "map_id" in spec:
            mid = spec["map_id"]
            if not isinstance(mid, str) or not MAP_ID.fullmatch(mid):
                raise ApiError(400, "invalid cover map_id")
            path, _ = self.api.cover(mid)
            loaded = read_cover(path)
            data = loaded[0] if loaded else None
        else:
            try:
                data = base64.b64decode(str(spec.get("data", "")), validate=True)
            except (binascii.Error, ValueError):
                raise ApiError(400, "cover data is not base64") from None
        if not data or len(data) > min(MAX_COVER, MAX_COVER_BYTES):
            raise ApiError(400, "cover is empty or over 2 MB")
        if image_type(data) is None:
            raise ApiError(400, "cover must be a PNG or JPEG image")
        return data, False

    def _fill(self, fields: dict, lib: Library) -> dict:
        """Remember each local song's current hash so a deleted map still exports."""
        for s in fields["songs"]:
            row = lib.by_id.get(s.get("map_id", ""))
            if row:
                s["hash"] = lib.hash_of(s["map_id"]) or s.get("hash")
                s["song_name"] = s["song_name"] or row["title"]
                s["mapper"] = s["mapper"] or row["mapper"]
            elif "map_id" in s and "hash" not in s:
                raise ApiError(404, f"unknown map: {s['map_id']}")
            if s.get("hash") is None:
                s.pop("hash", None)
        return fields

    def _item(self, map_id: str | None) -> dict | None:
        """The song's library item, shaped as in GET /api/maps, or None."""
        row = self.api.store.get_map(map_id) if map_id else None
        if row is None:
            return None
        return shape_item(row, self.api.service.levels, self.api.extras)

    def view(self, rec: dict, lib: Library, base: str, full: bool = False) -> dict:
        songs = resolve_all(rec, lib)
        has_cover = self.store.cover(rec["id"]) is not None
        out = {
            **{k: rec.get(k, "") for k in ("id", "title", "author", "description", "folder")},
            "sync": bool(rec.get("sync")),
            "exported": rec.get("exported", ""),
            "updated_at": rec.get("updated_at", ""),
            "songs_count": len(songs),
            "missing_count": sum(s["missing"] for s in songs),
            "cover_url": f"/api/playlists/{rec['id']}/cover?v={rec.get('updated_at', '')}"
            if has_cover
            else None,
            "sync_url": f"{self._base(base)}/api/playlists/{rec['id']}/bplist",
        }
        if full:
            for s in songs:
                s["cover_url"] = f"/api/maps/{s['map_id']}/cover" if s["map_id"] else None
                s["map"] = self._item(s["map_id"])
            out["songs"] = songs
        return out

    # CRUD ----------------------------------------------------------------------

    def listing(self, base: str) -> dict:
        lib = self._lib()
        return {"items": [self.view(r, lib, base) for r in self.store.list()]}

    def get(self, pid: str, base: str) -> dict:
        return self.view(self._rec(pid), self._lib(), base, full=True)

    def save(self, body: object, base: str, pid: str | None = None) -> dict:
        if pid:
            self._rec(pid)
        try:
            fields = clean_record(body)
        except PlaylistError as exc:
            raise ApiError(400, str(exc)) from None
        lib = self._lib()
        cover, clear = self._cover_from(body.get("cover") if isinstance(body, dict) else None)
        rec = self.store.save(self._fill(fields, lib), pid, cover, clear)
        return self.view(rec, lib, base, full=True)

    def delete(self, pid: str) -> dict:
        if not self.store.delete(pid):
            raise ApiError(404, f"unknown playlist: {pid}")
        return {"deleted": pid}

    def cover(self, pid: str) -> tuple[bytes, str]:
        data = self.store.cover(pid) if PLAYLIST_ID.fullmatch(pid) else None
        if data is None:
            raise ApiError(404, "no cover")
        return data, image_type(data) or "application/octet-stream"

    # documents -----------------------------------------------------------------

    def doc(self, pid: str, base: str) -> dict:
        """The live .bplist of a stored playlist, hashes recomputed now."""
        rec = self._rec(pid)
        url = f"{self._base(base)}/api/playlists/{pid}/bplist"
        return to_doc(rec, self._lib(), self.store.cover(pid), url)

    def _live_ids(self, name: str, lib: Library) -> list[str]:
        if name == "latest-fixed":
            rows = [r for r in lib.by_id.values() if r["folder"].endswith(FIXED_COPY_SUFFIX)]

            def stamp(r: dict) -> float:
                try:
                    return (self.api.service.levels / r["folder"]).stat().st_mtime
                except OSError:
                    return 0.0

            return [r["id"] for r in sorted(rows, key=stamp, reverse=True)][:LIVE_LIMIT]
        ids: list[str] = []
        for j in self.api.store.job_lists()["recent"]:
            if j["kind"] == "generate" and j["status"] == "done":
                ids += self._job_maps(j["id"], lib)
        return list(dict.fromkeys(ids))[:LIVE_LIMIT]

    def _job_maps(self, job_id: str, lib: Library) -> list[str]:
        if not JOB_ID.fullmatch(job_id):
            raise ApiError(404, f"unknown job: {job_id}")
        try:
            job = self.api.store.job(job_id)
        except KeyError:
            raise ApiError(404, f"unknown job: {job_id}") from None
        result = job.get("result")
        result = result or {}
        fixed = result.get("fixed_id")
        if isinstance(fixed, str) and fixed in lib.by_id:
            return [fixed]  # a fix job's output is the copy, not the untouched original
        found = [v for v in result.values() if isinstance(v, str) and v in lib.by_id]
        return list(dict.fromkeys(found))

    def picks(self, kind: str, name: str) -> dict:
        """Song stubs for a job's output ("job") or a live source ("live"), for the editor."""
        lib = self._lib()
        if kind == "job":
            ids = self._job_maps(name, lib)
        elif name in LIVE:
            ids = self._live_ids(name, lib)
        else:
            raise ApiError(404, f"unknown source: {name}")
        return {"items": [{"map_id": m, "song_name": lib.by_id[m]["title"],
                           "mapper": lib.by_id[m]["mapper"]} for m in ids]}  # fmt: skip

    def live_doc(self, name: str, base: str) -> dict:
        """A rolling .bplist of the newest generated or fixed maps."""
        if name not in LIVE:
            raise ApiError(404, f"unknown live playlist: {name}")
        lib = self._lib()
        songs = [self._entry(m, lib) for m in self._live_ids(name, lib)]
        url = f"{self._base(base)}/api/playlists/live/{name}.bplist"
        return build_doc(
            f"saber-tooth: {LIVE[name].lower()}", [s for s in songs if s], sync_url=url
        )

    @staticmethod
    def _entry(map_id: str, lib: Library) -> dict | None:
        h = lib.hash_of(map_id)
        row = lib.by_id[map_id]
        return (
            {"hash": h, "songName": row["title"], "levelAuthorName": row["mapper"]} if h else None
        )

    # build and export ----------------------------------------------------------

    def export(self, pid: str, body: object, base: str) -> dict:
        rec = self._rec(pid)
        sub = body.get("subfolder", rec.get("folder", "")) if isinstance(body, dict) else ""
        if not isinstance(sub, str):
            raise ApiError(400, "subfolder must be text")
        if self.export_dir is None or not self.export_dir.is_dir():
            raise ApiError(404, "playlist export is not enabled")
        doc = self.doc(pid, base)
        if not rec.get("sync"):
            doc.pop("customData", None)
        try:
            path = write_bplist(doc, self.export_dir, sub, rec.get("exported") or None)
        except BadSubfolder as exc:
            raise ApiError(400, str(exc)) from None
        except PlaylistsDisabled as exc:
            raise ApiError(404, str(exc)) from None
        rel = os.path.relpath(path, self.export_dir.resolve()).replace("\\", "/")
        self.store.save({"exported": rel, "folder": sub.strip()}, pid)
        return {"path": str(path), "relative": rel}

    def from_maps(self, body: object, base: str) -> dict:
        """Create a playlist from library maps, a job's output or a live source; optional export."""
        if not isinstance(body, dict):
            raise ApiError(400, "send a JSON object")
        lib = self._lib()
        ids: list[str] = []
        raw = body.get("map_ids", [])
        if not isinstance(raw, list) or not all(isinstance(m, str) for m in raw):
            raise ApiError(400, "map_ids must be a list of ids")
        ids += raw
        if body.get("job_id"):
            ids += self._job_maps(str(body["job_id"]), lib)
        if body.get("source"):
            if body["source"] not in LIVE:
                raise ApiError(400, f"source must be one of {', '.join(LIVE)}")
            ids += self._live_ids(body["source"], lib)
        if not ids:
            raise ApiError(400, "no maps to add")
        songs = []
        for m in dict.fromkeys(ids):
            if m not in lib.by_id:
                raise ApiError(404, f"unknown map: {m}")
            songs.append(clean_song({"map_id": m}))
        title = body.get("title") or LIVE.get(str(body.get("source")), "Playlist")
        made = self.save({**body, "title": title, "songs": songs, "cover": body.get("cover")}, base)
        out: dict = {"playlist": made}
        if body.get("export"):
            out.update(self.export(made["id"], {}, base))
        return out
