"""Folder and file names derived from BeatSaver metadata."""

import re

from saber_tooth.beatsaver.models import BsMap

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_KEY = re.compile(r"[0-9a-fA-F]{1,12}")
MAX_PART = 80


def clean_text(text: str, limit: int = MAX_PART) -> str:
    """Remove characters Windows paths forbid, collapse spaces, trim dots and length."""
    text = " ".join(_ILLEGAL.sub("", text).split())
    return text[:limit].strip(" .")


def folder_name_for(bs: BsMap) -> str:
    """`<key> (<songName> - <levelAuthorName>)`, safe on every platform."""
    if not _KEY.fullmatch(bs.id):
        raise ValueError(f"invalid BeatSaver id: {bs.id!r}")
    song = clean_text(bs.song_name or bs.name) or "Unknown"
    author = clean_text(bs.mapper) or "Unknown"
    return f"{bs.id.lower()} ({song} - {author})"
