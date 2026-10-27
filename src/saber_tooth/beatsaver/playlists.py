"""Export a selection of BeatSaver maps as a Beat Saber .bplist playlist."""

import base64
import json
from pathlib import Path

from saber_tooth.beatsaver.models import BsMap
from saber_tooth.beatsaver.naming import clean_text
from saber_tooth.safe_fs import windows_safe_component

MAX_TRIES = 1000


class PlaylistsDisabled(Exception):
    """No playlists folder is configured or it does not exist."""


def export_bplist(
    title: str, maps: list[BsMap], dest_dir: Path | None, cover: bytes | None = None
) -> Path:
    """Write `<title>.bplist` into dest_dir, never overwriting: a taken name gets ` (2)`."""
    if dest_dir is None or not Path(dest_dir).is_dir():
        raise PlaylistsDisabled("playlist export is not configured")
    shown = " ".join(title.split())[:120] or "Playlist"
    doc: dict = {
        "playlistTitle": shown,
        "playlistAuthor": "saber-tooth",
        "songs": [
            {"key": m.id, "hash": m.hash, "songName": m.song_name or m.name,
             "levelAuthorName": m.mapper}
            for m in maps
        ],
    }  # fmt: skip
    if cover:
        doc["image"] = "base64," + base64.b64encode(cover).decode("ascii")
    text = json.dumps(doc, indent=2, ensure_ascii=False)
    stem = clean_text(shown, 100) or "Playlist"
    if not windows_safe_component(f"{stem}.bplist") or not windows_safe_component(
        f"{stem} (99).bplist"
    ):
        stem = f"playlist-{stem}"
    for n in range(1, MAX_TRIES + 1):
        path = Path(dest_dir) / (f"{stem}.bplist" if n == 1 else f"{stem} ({n}).bplist")
        try:
            with path.open("x", encoding="utf-8") as out:
                out.write(text)
        except FileExistsError:
            continue
        return path
    raise PlaylistsDisabled("too many playlists with this name")
