"""Proposal and finding views of one map: what the proposals and findings routes return."""

from pathlib import Path
from typing import TYPE_CHECKING

from saber_tooth.api.overlap import conflicts_with
from saber_tooth.api.wall_context import changed_walls, stored_walls, walls_context

if TYPE_CHECKING:
    from saber_tooth.api.core import Api

PROPOSAL_FIELDS = (
    "id",
    "rule",
    "difficulty",
    "severity",
    "summary",
    "status",
    "before",
    "after",
    "replaces",
)


def _stored_walls(api: "Api", map_id: str) -> dict[str, list[dict]]:
    row = next((m for m in api.store.list_maps() if m["id"] == map_id), None)
    if row is None or row["parse_error"]:
        return {}
    name = row["folder"]
    folder = api.service.levels / name
    if Path(name).name != name or folder.is_symlink() or not folder.is_dir():
        return {}
    return stored_walls(folder)


def _view(proposal: dict, stored: dict[str, list[dict]], clashes: dict[int, list[int]]) -> dict:
    view = {k: proposal[k] for k in PROPOSAL_FIELDS}
    view["conflicts_with"] = clashes.get(proposal["id"], [])
    before, after = changed_walls(proposal)
    context = walls_context(proposal, stored, before + after)
    view.update(walls_before=before, walls_after=after, walls_context=context)
    if view["status"] == "applying":
        view["status"] = "approved"
    return view


def proposal_views(api: "Api", map_id: str) -> list[dict]:
    found = api.store.proposals(api.map_id(map_id))
    stored = _stored_walls(api, map_id)
    clashes = conflicts_with(found)
    return [_view(p, stored, clashes) for p in found]


def map_findings(api: "Api", map_id: str) -> dict:
    """The latest scan's findings, each with the id of its proposal when one exists."""
    mid = api.map_id(map_id)
    info = api.store.scan_info(mid)
    if info is None:
        return {"scanned": False, "findings": []}
    row = api.store.get_map(mid) or {}
    bpm = row.get("bpm")

    def key(f: dict) -> tuple:
        return (f["rule"], f["difficulty"], f["beat_start"], f["beat_end"], f["message"])

    owners = {
        key(p["finding"]): p["id"]
        for p in api.store.proposals(mid)
        if p["finding"] and p["status"] != "superseded"
    }
    out = []
    for f in info["findings"]:
        view = {k: f[k] for k in ("rule", "difficulty", "beat_start", "beat_end", "severity")}
        view["message"] = f["message"]
        view["time_s"] = round(f["beat_start"] * 60 / bpm, 2) if bpm else None
        view["proposal_id"] = owners.get(key(f))
        view["unfixed_reason"] = f.get("unfixed_reason")
        out.append(view)
    return {"scanned": True, "findings": out}
