"""Song name, sub name and author for a generated map, from a project name or audio tags."""

import re
from dataclasses import dataclass
from pathlib import Path

from saber_tooth.audio import probe_info
from saber_tooth.mapio import load_map

UNKNOWN_AUTHOR = "Unknown"
FIELD_MAX = 120
_BRACKETS = re.compile(r"[(\[]([^()\[\]]*)[)\]]")
_DASH = re.compile(r"\s+[-" + chr(0x2013) + chr(0x2014) + r"]\s+")  # hyphen, en and em dash
_TOPIC = re.compile(r"\s+-\s+Topic$", re.IGNORECASE)


@dataclass(frozen=True)
class SongMeta:
    song: str
    sub: str
    author: str


def _tidy(text: str) -> str:
    return " ".join(text.split())[:FIELD_MAX].strip()


def parse_title(title: str, channel: str = "") -> SongMeta:
    """Split "Artist (Tag) - Song" into author, sub name and song.

    The channel is the fallback author.
    """
    whole = _tidy(title)
    tags = [t for t in (_tidy(m) for m in _BRACKETS.findall(whole)) if t]
    text = _tidy(_BRACKETS.sub(" ", whole))
    sub = _tidy(", ".join(tags))
    fallback = _tidy(_TOPIC.sub("", channel)) or UNKNOWN_AUTHOR
    if not text:
        return SongMeta(whole or "Untitled", "", fallback)
    parts = _DASH.split(text, maxsplit=1)
    if len(parts) == 2 and _tidy(parts[0]) and _tidy(parts[1]):
        return SongMeta(_tidy(parts[1]), sub, _tidy(parts[0]))
    return SongMeta(text, sub, fallback)


def file_meta(file_name: str, tags: dict[str, str]) -> SongMeta:
    """Meta from the title and artist tags, else from the file name without its extension."""
    title = tags.get("title", "").strip()
    if title:
        return parse_title(title, tags.get("artist", ""))
    return parse_title(Path(file_name).stem, tags.get("artist", ""))


def project_meta(name: str) -> SongMeta:
    """Meta from a beat-analyser project name: the video title, spaces written as underscores."""
    return parse_title(name.replace("_", " "))


def _number(text: str | None) -> float | None:
    try:
        value = float(str(text).strip())
    except ValueError:
        return None
    return round(value, 3) if value > 0 else None


def describe(path: Path) -> dict:
    """Title, artist, duration (seconds) and bpm of an audio file or a map folder.

    A map answers from its info.dat and its song file; an audio file from its tags, else its
    file name. Values that cannot be read are None."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no such file or folder: {path}")
    if path.is_file() and path.name.lower() == "info.dat":
        path = path.parent
    if path.is_dir():
        info = load_map(path).info
        probed = probe_info(path / info.song_file)
        return {
            "title": info.song_name,
            "artist": info.author,
            "duration": probed["duration"],
            "bpm": info.bpm,
        }
    probed = probe_info(path)
    tags = probed["tags"]
    meta = file_meta(path.name, tags)
    return {
        "title": meta.song,
        "artist": meta.author if meta.author != UNKNOWN_AUTHOR else None,
        "duration": probed["duration"],
        "bpm": _number(tags.get("bpm") or tags.get("tbpm")),
    }
