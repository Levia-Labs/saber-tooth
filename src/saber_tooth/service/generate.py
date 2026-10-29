"""One-step generation: analyse, build, fix and write a finished map into the levels folder."""

import hashlib
import logging
import shutil
import uuid
from pathlib import Path

from saber_tooth.analysis import Analysis
from saber_tooth.assemble import assemble_new, folder_name
from saber_tooth.checks import run_checks
from saber_tooth.mapio import load_map, write_map
from saber_tooth.service.fix import complete, fix_beatmap
from saber_tooth.service.util import checkpoint, map_id_for
from saber_tooth.service.writeout import commit_staged
from saber_tooth.songmeta import SongMeta, file_meta, project_meta

log = logging.getLogger(__name__)


def _is_url(source: str) -> bool:
    return source.startswith(("http://", "https://"))


def _meta(svc, source: str, a: Analysis) -> SongMeta:
    """Names from the video title beat-analyser names a project after, else tags or file name."""
    if _is_url(source):
        return project_meta(a.name)
    path = Path(source)
    return file_meta(path.name, svc.probe_tags(path))


def _fix_in_place(svc, staging: Path, a: Analysis, seed: int, progress=None) -> int:
    """Run the Fix engine on the staged map and write the result back; the fixes applied."""
    check = getattr(progress, "check", None)
    run = fix_beatmap(load_map(staging), a, svc._templates(), seed, check=check)
    checkpoint(progress)
    if run.steps:
        write_map(run.fixed, staging, None)
    return len(run.steps)


def generate_map(svc, source: str, progress=None) -> dict:
    """Generate a map from a YouTube URL or an audio file path into a new levels folder.

    The map is built and fixed in a staging folder, then moved into the levels folder under a
    numbered name when one exists already; staging is removed on success and on any failure."""
    checkpoint(progress, "analysing the song")
    if _is_url(source):
        a = svc.client.analyse_url(source)
    else:
        a = svc.client.analyse_file(Path(source), Path(source).name)
    checkpoint(progress, "building the map")
    meta = _meta(svc, source, a)
    staging = svc.data / "staging" / uuid.uuid4().hex
    staging.parent.mkdir(parents=True, exist_ok=True)
    seed = int(hashlib.sha256(a.name.encode("utf-8")).hexdigest()[:8], 16)
    try:
        assemble_new(a, svc._templates(), staging, seed, svc.encode, meta)
        checkpoint(progress, "fixing the map")
        fixes = _fix_in_place(svc, staging, a, seed, progress)
        written = load_map(staging)
        checkpoint(progress, "saving the map")  # staging is removed below on a cancel
        with svc._lock:
            target = commit_staged(svc.levels, staging, folder_name(meta.song))
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    try:
        svc.refresh_library()
    except Exception:
        log.exception("library refresh failed after generating %s", target.name)
    map_id = map_id_for(target.name)
    project = a.audio.parent.name if a.audio else None
    findings = run_checks(written, a)
    scan = {"findings": [f.to_dict() for f in findings], "analysis": project}
    with svc._lock:
        svc.store.replace_open_proposals(map_id, [], scan)
    return {
        "map_id": map_id,
        "folder": target.name,
        "fixes": fixes,
        "errors": sum(f.severity == "error" for f in findings),
        "complete": complete(written),
    }
