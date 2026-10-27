"""Typed views of the BeatSaver MapDetail and Playlist JSON; parsing tolerates missing keys."""

from dataclasses import asdict, dataclass
from typing import Any


def _num(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value)


def _int(value: Any) -> int:
    return int(_num(value))


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class BsDiff:
    characteristic: str
    difficulty: str
    nps: float
    njs: float
    notes: int
    seconds: float

    @classmethod
    def from_json(cls, d: dict) -> "BsDiff":
        return cls(
            _text(d.get("characteristic")),
            _text(d.get("difficulty")),
            _num(d.get("nps")),
            _num(d.get("njs")),
            _int(d.get("notes")),
            _num(d.get("seconds")),
        )


@dataclass(frozen=True)
class BsMap:
    id: str
    name: str
    song_name: str
    song_sub: str
    song_author: str
    mapper: str
    bpm: float
    duration: int
    score: float
    upvotes: int
    downvotes: int
    tags: tuple[str, ...]
    ranked: bool
    hash: str
    download_url: str
    cover_url: str
    preview_url: str
    diffs: tuple[BsDiff, ...]
    uploaded: str

    @classmethod
    def from_json(cls, d: dict) -> "BsMap":
        """Parse a BeatSaver MapDetail; uses the newest published version (else the newest)."""
        meta, stats = _dict(d.get("metadata")), _dict(d.get("stats"))
        versions = [v for v in d.get("versions") or [] if isinstance(v, dict)]
        published = [v for v in versions if v.get("state") == "Published"]
        ver = (published or versions or [{}])[-1]
        diffs = tuple(BsDiff.from_json(x) for x in ver.get("diffs") or [] if isinstance(x, dict))
        tags = tuple(t for t in d.get("tags") or [] if isinstance(t, str))
        ranked = bool(d.get("ranked") or d.get("blRanked") or d.get("qualified"))
        return cls(
            _text(d.get("id")),
            _text(d.get("name")),
            _text(meta.get("songName")),
            _text(meta.get("songSubName")),
            _text(meta.get("songAuthorName")),
            _text(meta.get("levelAuthorName")) or _text(_dict(d.get("uploader")).get("name")),
            _num(meta.get("bpm")),
            _int(meta.get("duration")),
            _num(stats.get("score")),
            _int(stats.get("upvotes")),
            _int(stats.get("downvotes")),
            tags,
            ranked,
            _text(ver.get("hash")).lower(),
            _text(ver.get("downloadURL")),
            _text(ver.get("coverURL")),
            _text(ver.get("previewURL")),
            diffs,
            _text(d.get("uploaded")),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BsMap":
        """Rebuild from `to_dict` output (the cache format)."""
        d = dict(d)
        d["tags"] = tuple(d.get("tags") or ())
        d["diffs"] = tuple(BsDiff(**x) for x in d.get("diffs") or ())
        return cls(**d)


@dataclass(frozen=True)
class BsPlaylist:
    id: int
    name: str
    owner: str
    maps_count: int
    min_nps: float
    max_nps: float
    cover_url: str

    @classmethod
    def from_json(cls, d: dict) -> "BsPlaylist":
        stats = _dict(d.get("stats"))
        return cls(
            _int(d.get("playlistId")),
            _text(d.get("name")),
            _text(_dict(d.get("owner")).get("name")),
            _int(stats.get("totalMaps")),
            _num(stats.get("minNps")),
            _num(stats.get("maxNps")),
            _text(d.get("playlistImage512") or d.get("playlistImage")),
        )
