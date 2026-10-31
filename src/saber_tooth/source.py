"""Where a generated map came from: a stable source key, and the video title for a link.

A YouTube link of any form (watch?v=, youtu.be/, shorts/, music.youtube.com, extra parameters)
becomes `yt:<video id>`; an uploaded file becomes `sha256:<content hash>`.
"""

import hashlib
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_PATH_FORMS = ("shorts", "embed", "live", "v")
OEMBED = "https://www.youtube.com/oembed"
TITLE_TIMEOUT_S = 4.0
_CHUNK = 1024 * 1024


def youtube_id(url: str) -> str | None:
    """The video id in a YouTube link, or None when the link names no video."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    parts = [p for p in parsed.path.split("/") if p]
    found: str | None = None
    if host == "youtu.be":
        found = parts[0] if parts else None
    elif host.endswith("youtube.com"):
        if parts[:1] == ["watch"]:
            found = (parse_qs(parsed.query).get("v") or [None])[0]
        elif len(parts) >= 2 and parts[0] in _PATH_FORMS:
            found = parts[1]
    return found if found and _ID.fullmatch(found) else None


def url_source(url: str) -> str:
    """`yt:<id>` for a video link; other links fall back to the trimmed link itself."""
    vid = youtube_id(url)
    return f"yt:{vid}" if vid else f"url:{url.strip()}"


def file_source(path: Path) -> str:
    """`sha256:<hash>` of the file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def video_title(url: str, timeout: float = TITLE_TIMEOUT_S) -> str | None:
    """The video's title from YouTube's oEmbed answer; None when it is slow, offline or private."""
    vid = youtube_id(url)
    if vid is None:
        return None
    try:
        reply = httpx.get(
            OEMBED,
            params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"},
            timeout=timeout,
        )
        title = reply.json().get("title") if reply.status_code == 200 else None
    except (httpx.HTTPError, ValueError, AttributeError):
        return None
    return title.strip() or None if isinstance(title, str) else None
