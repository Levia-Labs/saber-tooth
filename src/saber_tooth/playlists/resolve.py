"""Resolve stored playlist songs against the library and build the .bplist document."""

from pathlib import Path

from saber_tooth.beatsaver.playlists import DEFAULT_AUTHOR, build_doc
from saber_tooth.playlists.songcore import HashCache

CACHE = HashCache()


class Library:
    """Library rows by id, and a hash index built only when a hash-only song needs it."""

    def __init__(self, rows: list[dict], levels: Path, cache: HashCache = CACHE) -> None:
        self.levels, self.cache = levels, cache
        self.by_id = {r["id"]: r for r in rows}
        self._by_hash: dict[str, str] | None = None

    def hash_of(self, map_id: str) -> str | None:
        row = self.by_id.get(map_id)
        if row is None or row.get("parse_error"):
            return None
        name = row["folder"]
        folder = self.levels / name
        if Path(name).name != name or folder.is_symlink():
            return None
        return self.cache.get(folder)

    def find(self, hash_: str) -> str | None:
        if self._by_hash is None:
            self._by_hash = {}
            for mid in self.by_id:
                h = self.hash_of(mid)
                if h:
                    self._by_hash.setdefault(h, mid)
        return self._by_hash.get(hash_.upper())


def resolve_song(song: dict, lib: Library) -> dict:
    """The song as shown: current hash, library id, and whether nothing installed matches."""
    mid = song.get("map_id")
    h = lib.hash_of(mid) if mid else None
    if mid is None and song.get("hash"):
        mid = lib.find(song["hash"])
        h = song["hash"].upper() if mid else None
    row = lib.by_id.get(mid) if mid and h else None
    return {
        "map_id": mid if row else None,
        "hash": h or song.get("hash"),
        "key": song.get("key"),
        "song_name": (row["title"] if row else None) or song.get("song_name") or "",
        "mapper": (row["mapper"] if row else None) or song.get("mapper") or "",
        "missing": h is None,
    }


def resolve_all(rec: dict, lib: Library) -> list[dict]:
    return [resolve_song(s, lib) for s in rec.get("songs", [])]


def to_doc(rec: dict, lib: Library, cover: bytes | None, sync_url: str | None) -> dict:
    """The live .bplist: hashes recomputed now; songs with no known hash are left out."""
    songs = []
    for s in resolve_all(rec, lib):
        if not s["hash"]:
            continue
        entry = {"hash": s["hash"], "songName": s["song_name"], "levelAuthorName": s["mapper"]}
        if s["key"]:
            entry["key"] = s["key"]
        songs.append(entry)
    return build_doc(
        rec["title"],
        songs,
        author=rec.get("author") or DEFAULT_AUTHOR,
        description=rec.get("description", ""),
        cover=cover,
        sync_url=sync_url if rec.get("sync") else None,
    )
