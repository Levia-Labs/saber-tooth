"""Song name, sub name and author for a generated map, from a project name or audio tags."""

import re
from dataclasses import dataclass
from pathlib import Path

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
