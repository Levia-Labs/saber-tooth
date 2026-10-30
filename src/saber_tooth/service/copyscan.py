"""Scan rows for saber-tooth copies, stored when the copy is written so it is never unscanned."""

from saber_tooth.checks import run_checks
from saber_tooth.model import Beatmap
from saber_tooth.service.util import map_id_for


def store_copy_scan(svc, folder_name: str, beatmap: Beatmap, analysis, locked: bool = True) -> None:
    """Save the copy's own findings (one whole-map check, no proposals) as its scan."""
    project = analysis.audio.parent.name if analysis and analysis.audio else None
    scan = {"findings": [f.to_dict() for f in run_checks(beatmap, analysis)], "analysis": project}
    if not locked:  # the caller already holds the service lock
        svc.store.replace_open_proposals(map_id_for(folder_name), [], scan)
        return
    with svc._lock:
        svc.store.replace_open_proposals(map_id_for(folder_name), [], scan)
