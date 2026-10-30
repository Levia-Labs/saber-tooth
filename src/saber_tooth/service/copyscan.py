"""Scan rows for saber-tooth copies, stored when the copy is written so it is never unscanned."""

import re

from saber_tooth.checks import run_checks
from saber_tooth.model import Beatmap
from saber_tooth.service.util import map_id_for

_CROP = re.compile(r" \[(?:1 min|2 min|crop [^\]]*)\]$")
_FIX = " [saber-tooth]"


def is_copy(name: str) -> bool:
    """A folder written by Fix, relight, apply or crop: its status is known without a scan."""
    return name.endswith(_FIX) or _CROP.search(name) is not None


def copy_source(name: str) -> str:
    """The folder a copy came from: the crop label and the saber-tooth suffix removed."""
    name = _CROP.sub("", name)
    return name[: -len(_FIX)] if name.endswith(_FIX) else name


def store_copy_scan(svc, folder_name: str, beatmap: Beatmap, analysis, locked: bool = True) -> None:
    """Save the copy's own findings (one whole-map check, no proposals) as its scan."""
    project = analysis.audio.parent.name if analysis and analysis.audio else None
    scan = {"findings": [f.to_dict() for f in run_checks(beatmap, analysis)], "analysis": project}
    if not locked:  # the caller already holds the service lock
        svc.store.replace_open_proposals(map_id_for(folder_name), [], scan)
        return
    with svc._lock:
        svc.store.replace_open_proposals(map_id_for(folder_name), [], scan)
