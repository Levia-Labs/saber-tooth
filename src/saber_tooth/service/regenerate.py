"""Regenerate: rerun the full generator on a generated map's own audio and swap the result in.

The folder name, map id, title, artist, cover and any environment or colours chosen since the
first run are kept. The new map is built in staging; the previous version is copied to
`<data>/backups/<folder>` before the swap, so one earlier version always stays."""

import hashlib
import logging
import shutil
import uuid
from pathlib import Path

from saber_tooth.assemble import COVER_FILE, SONG_FILE, assemble_new
from saber_tooth.checks import run_checks
from saber_tooth.copynames import is_fixed_copy, strip_fixed
from saber_tooth.crop.replace import replace_folder
from saber_tooth.fixer import ApplyLightshow, apply_ops
from saber_tooth.fixer.verify import map_timing
from saber_tooth.generated import is_generated
from saber_tooth.lightshow import build_lightshow
from saber_tooth.mapio import load_map, write_map
from saber_tooth.service.fix import complete
from saber_tooth.service.generate import _fix_in_place, _is_url
from saber_tooth.service.relight import SUFFIX, environment_names
from saber_tooth.service.util import checkpoint
from saber_tooth.service.writeout import commit_staged
from saber_tooth.songmeta import SongMeta

log = logging.getLogger(__name__)
BACKUPS = "backups"


class NotGenerated(ValueError):
    """The map has no recorded source: it is human-made and is never regenerated."""


def map_source(store, map_id: str) -> str:
    """The recorded source key; empty for a map known only by its author name."""
    rows = store._query("SELECT source FROM maps WHERE id=?", (map_id,))
    return (rows[0]["source"] or "") if rows else ""


def _link(source: str) -> str | None:
    """The video link a source key stands for; None for a file hash."""
    if source.startswith("yt:"):
        return f"https://www.youtube.com/watch?v={source[3:]}"
    if source.startswith("url:") and _is_url(source[4:]):
        return source[4:]
    return None


def _analyse(svc, source: str, folder: Path):
    """The song's analysis from the kept audio, else from the stored source link."""
    egg = folder / SONG_FILE
    if egg.is_file():
        # song.egg is Ogg Vorbis; the analyser validates by extension, so send it as .ogg
        return svc.client.analyse_file(egg, "song.ogg")
    link = _link(source)
    if link:
        return svc.client.analyse_url(link)
    raise FileNotFoundError(f"no {SONG_FILE} in {folder.name} and its source is not a link")


def keeps_look(svc, map_id: str, folder: Path, old) -> bool:
    """True when the map's environment and colours were chosen: it has a colour scheme, or a
    relight job set its environment. Otherwise the auto-style restyles it."""
    if old.info.color_scheme is not None or folder.name.endswith(SUFFIX):
        return True
    rows = svc.store._query(
        "SELECT 1 FROM jobs WHERE map_id=? AND kind='relight' AND status='done' LIMIT 1",
        (map_id,),
    )
    return bool(rows)


def _keep_look(svc, staging: Path, old, a, seed: int) -> None:
    """Carry the old environment, colour scheme and cover into the staged map."""
    staged = load_map(staging)
    env = old.info.environment
    if env != staged.info.environment and env in environment_names(svc._templates()):
        payload = build_lightshow(staged, map_timing(staged), svc._templates(), a, seed, env)
        staged = apply_ops(staged, [ApplyLightshow.from_payload(payload)])
    if old.info.color_scheme is not None:
        staged.info.color_scheme = old.info.color_scheme
    write_map(staged, staging, None)


def _keep_cover(folder: Path, old, staging: Path) -> None:
    cover = folder / old.info.cover_file
    if not old.info.cover_file or cover.parent != folder or not cover.is_file():
        return
    if cover.name != COVER_FILE:
        (staging / COVER_FILE).unlink(missing_ok=True)
        staged = load_map(staging)
        staged.info.cover_file = cover.name
        write_map(staged, staging, None)
    shutil.copyfile(cover, staging / cover.name)


def _backup(svc, folder: Path) -> Path:
    dest = svc.data / BACKUPS / folder.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{folder.name}.partial")
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(folder, tmp)
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    return dest


def _drop_copies(svc, folder: Path) -> None:
    """The regenerated map is clean by contract: its fixed copies are stale and go."""
    if is_fixed_copy(folder.name):
        return
    for other in svc.levels.iterdir():
        if other.is_dir() and is_fixed_copy(other.name) and strip_fixed(other.name) == folder.name:
            shutil.rmtree(other, ignore_errors=True)


def regenerate_map(svc, map_id: str, progress=None) -> dict:
    """Rebuild one generated map in place; `NotGenerated` for a map without a source."""
    if not is_generated(svc.store, svc.levels, map_id):
        raise NotGenerated("only generated maps can be regenerated")
    folder = svc._folder(map_id)
    old = svc._load(folder)
    checkpoint(progress, "analysing the song")
    a = _analyse(svc, map_source(svc.store, map_id), folder)
    checkpoint(progress, "building the map")
    meta = SongMeta(old.info.song_name, old.info.sub_name, old.info.author)
    staging = svc.data / "staging" / uuid.uuid4().hex
    staging.parent.mkdir(parents=True, exist_ok=True)
    seed = int(hashlib.sha256(a.name.encode("utf-8")).hexdigest()[:8], 16)
    try:
        assemble_new(a, svc._templates(), staging, seed, svc.encode, meta)
        checkpoint(progress, "fixing the map")
        fixes = _fix_in_place(svc, staging, a, seed, progress)
        if keeps_look(svc, map_id, folder, old):
            _keep_look(svc, staging, old, a, seed)
        _keep_cover(folder, old, staging)
        written = load_map(staging)
        checkpoint(progress, "saving the map")  # staging is removed below on a cancel
        with svc._lock:
            _backup(svc, folder)
            partial = commit_staged(svc.levels, staging, folder.name + " regen-tmp")
            replace_folder(svc.levels, folder, partial)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    _drop_copies(svc, folder)
    try:
        svc.refresh_library()
    except Exception:
        log.exception("library refresh failed after regenerating %s", folder.name)
    project = a.audio.parent.name if a.audio else None
    findings = run_checks(written, a)
    scan = {"findings": [f.to_dict() for f in findings], "analysis": project}
    with svc._lock:
        svc.store.replace_open_proposals(map_id, [], scan)
    return {
        "map_id": map_id,
        "folder": folder.name,
        "fixes": fixes,
        "errors": sum(f.severity == "error" for f in findings),
        "complete": complete(written),
    }
