"""Write a Beat Saber .bplist playlist: BeatSaver selections and local maps share this."""

import base64
import json
import os
import tempfile
from pathlib import Path

from saber_tooth.beatsaver.models import BsMap
from saber_tooth.beatsaver.naming import clean_text
from saber_tooth.safe_fs import windows_safe_component

MAX_TRIES = 1000
MAX_DEPTH = 3
DEFAULT_AUTHOR = "saber-tooth"


class PlaylistsDisabled(Exception):
    """No playlists folder is configured or it does not exist."""


class BadSubfolder(ValueError):
    """The requested subfolder is not a plain relative path of safe names."""


def shown_title(title: str) -> str:
    return " ".join(title.split())[:120] or "Playlist"


def subfolder_parts(sub: str | None) -> tuple[str, ...]:
    """Validated components of a relative subfolder; raises BadSubfolder on anything else."""
    if sub is None or not sub.strip():
        return ()
    if sub.startswith(("/", "\\")) or ":" in sub:
        raise BadSubfolder("subfolder must be a relative path")
    parts = tuple(p for p in sub.replace("\\", "/").split("/") if p)
    if len(parts) > MAX_DEPTH:
        raise BadSubfolder(f"subfolder is at most {MAX_DEPTH} levels deep")
    for p in parts:
        if not windows_safe_component(p):
            raise BadSubfolder(f"invalid subfolder name: {p!r}")
    return parts


def target_dir(dest_dir: Path | None, sub: str | None) -> Path:
    """dest_dir plus the validated subfolder (created), never outside dest_dir."""
    if dest_dir is None or not Path(dest_dir).is_dir():
        raise PlaylistsDisabled("playlist export is not configured")
    root = Path(dest_dir).resolve()
    path = root
    for part in subfolder_parts(sub):
        path = path / part
        if path.is_symlink() or path.is_junction():
            raise BadSubfolder(f"subfolder is a link: {part!r}")
    path.mkdir(parents=True, exist_ok=True)
    if path.resolve() != root and root not in path.resolve().parents:
        raise BadSubfolder("subfolder leaves the playlists folder")
    return path


def build_doc(
    title: str,
    songs: list[dict],
    *,
    author: str = DEFAULT_AUTHOR,
    description: str = "",
    cover: bytes | None = None,
    sync_url: str | None = None,
) -> dict:
    """A .bplist document; each song is {hash, songName, levelAuthorName[, key]}."""
    doc: dict = {
        "playlistTitle": shown_title(title),
        "playlistAuthor": " ".join(author.split())[:120] or DEFAULT_AUTHOR,
    }
    if description.strip():
        doc["playlistDescription"] = description.strip()[:2000]
    doc["songs"] = songs
    if cover:
        doc["image"] = "base64," + base64.b64encode(cover).decode("ascii")
    if sync_url:
        doc["customData"] = {"syncURL": sync_url}
    return doc


def _atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(text)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_bplist(
    doc: dict, dest_dir: Path | None, sub: str | None = None, replace: str | None = None
) -> Path:
    """Write the doc into dest_dir/sub as `<title>.bplist`, never overwriting another file.

    `replace` names a file (relative to dest_dir) this playlist wrote before; it is rewritten
    in place when it still sits in the requested subfolder."""
    folder = target_dir(dest_dir, sub)
    text = json.dumps(doc, indent=2, ensure_ascii=False)
    if replace:
        old = Path(dest_dir) / replace
        if old.parent.resolve() == folder.resolve() and old.is_file() and not old.is_symlink():
            _atomic(old, text)
            return old
    stem = clean_text(doc["playlistTitle"], 100) or "Playlist"
    if not windows_safe_component(f"{stem}.bplist") or not windows_safe_component(
        f"{stem} (99).bplist"
    ):
        stem = f"playlist-{stem}"
    for n in range(1, MAX_TRIES + 1):
        path = folder / (f"{stem}.bplist" if n == 1 else f"{stem} ({n}).bplist")
        try:
            with path.open("x", encoding="utf-8") as out:
                out.write(text)
        except FileExistsError:
            continue
        return path
    raise PlaylistsDisabled("too many playlists with this name")


def export_bplist(
    title: str,
    maps: list[BsMap],
    dest_dir: Path | None,
    cover: bytes | None = None,
    sub: str | None = None,
) -> Path:
    """Write BeatSaver maps as `<title>.bplist`; a taken name gets ` (2)`."""
    songs = [
        {"key": m.id, "hash": m.hash, "songName": m.song_name or m.name,
         "levelAuthorName": m.mapper}
        for m in maps
    ]  # fmt: skip
    return write_bplist(build_doc(title, songs, cover=cover), dest_dir, sub)
