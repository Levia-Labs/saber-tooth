"""MCP tools: thin wrappers over the same Api calls the REST routes use."""

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from saber_tooth.api.beatsaver import BeatSaverApi
from saber_tooth.api.core import Api, ApiError
from saber_tooth.api.crop_api import CropApi

MAX_MAPS = 200
MAX_PROPOSALS = 200

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
SAFE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
JOB = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
WEB = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)


def build_mcp(api: Api, bs: BeatSaverApi | None = None, crop: CropApi | None = None) -> MCPServer:
    mcp = MCPServer("saber-tooth", instructions="Review and fix Beat Saber custom levels.")

    @mcp.tool(annotations=READ)
    def list_maps(filter: str = "") -> dict[str, Any]:
        """List indexed maps (id, title, mapper, bpm, status, job); filter is a substring."""
        page = api.maps_page({"q": filter[:200], "limit": str(MAX_MAPS)}, MAX_MAPS)
        return {"total": page["total"], "maps": page["items"]}

    @mcp.tool(annotations=READ)
    def get_proposals(map_id: str) -> dict[str, Any]:
        """List fix proposals for a map, with their status."""
        rows = api.proposals(map_id)
        return {"total": len(rows), "proposals": rows[:MAX_PROPOSALS]}

    @mcp.tool(annotations=JOB)
    def scan_map(map_id: str) -> dict[str, Any]:
        """Start a scan of one map; returns a job id for job_status."""
        return api.scan(map_id)

    @mcp.tool(annotations=READ)
    def job_status(job_id: str) -> dict[str, Any]:
        """Status, error and result of a job started by another tool."""
        return api.job(job_id)

    @mcp.tool(annotations=SAFE)
    def approve_proposal(id: str) -> dict[str, Any]:
        """Mark a proposal approved. Nothing is written until apply_map."""
        return api.set_status(id, "approved")

    @mcp.tool(annotations=SAFE)
    def reject_proposal(id: str) -> dict[str, Any]:
        """Mark a proposal rejected."""
        return api.set_status(id, "rejected")

    @mcp.tool(annotations=JOB)
    def apply_map(map_id: str) -> dict[str, Any]:
        """Apply approved proposals; returns a job id. The only tool that writes into
        CustomLevels, and only as a new folder: the original map is never edited."""
        return api.apply(map_id)

    @mcp.tool(annotations=JOB)
    def fix_map(map_id: str) -> dict[str, Any]:
        """One-click fix: adds missing difficulties and fixes every error, writing a new
        '<map> [saber-tooth]' folder; the original is never changed. Returns a job id whose
        result is the before/after report."""
        return api.fix(map_id)

    @mcp.tool(annotations=WEB)
    def generate_from_youtube(url: str) -> dict[str, Any]:
        """Generate a new map from a YouTube URL (youtube.com or youtu.be); returns a job id."""
        return api.generate_url(url)

    @mcp.tool(annotations=JOB)
    def learn_lightshows() -> dict[str, Any]:
        """Learn lighting patterns from the indexed library; returns a job id."""
        return api.learn()

    if bs is not None:
        _beatsaver_tools(mcp, bs)
    if crop is not None:
        _crop_tools(mcp, crop)
    return mcp


def _beatsaver_tools(mcp: MCPServer, bs: BeatSaverApi) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
    def beatsaver_search(
        q: str = "",
        tags: str = "",
        min_rating: float | None = None,
        nps_min: float | None = None,
        nps_max: float | None = None,
        nps_scope: str = "any",
        diffs: str = "",
        diffs_mode: str = "all",
        cursor: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search BeatSaver; tags and diffs are comma lists (diffs: Easy..ExpertPlus, Standard
        only). Filters BeatSaver lacks run locally. Pass the returned cursor to continue."""
        values = {
            "q": q, "tags": tags, "nps_scope": nps_scope, "diffs": diffs,
            "diffs_mode": diffs_mode, "cursor": cursor, "limit": str(limit),
            "min_rating": "" if min_rating is None else str(min_rating),
            "nps_min": "" if nps_min is None else str(nps_min),
            "nps_max": "" if nps_max is None else str(nps_max),
        }  # fmt: skip
        return bs.search(values, MAX_MAPS)

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)
    )
    def beatsaver_download(ids: list[str]) -> dict[str, Any]:
        """Download BeatSaver maps (up to 100 keys) into CustomLevels as new folders; maps
        already installed are skipped. Returns a job id for job_status."""
        return bs.download({"ids": ids})


def _crop_tools(mcp: MCPServer, crop: CropApi) -> None:
    @mcp.tool(annotations=READ)
    def map_timeline(map_id: str) -> dict[str, Any]:
        """Notes per second per difficulty, the song sections with intensity and, for 1 and
        2 minute crops, the suggested windows and every allowed start and end point. Times are
        in beats and seconds; an analysed map gives better sections than `map_only` ones."""
        try:
            return crop.timeline(map_id)
        except ApiError as exc:
            raise ToolError(str(exc)) from None

    @mcp.tool(annotations=JOB)
    def crop_map(map_id: str, start_beat: float, end_beat: float) -> dict[str, Any]:
        """Crop a map to a 1 or 2 minute highlight: writes a new '<map> [1 min]' or
        '[2 min]' folder; the original is never changed. start_beat and end_beat must be a start
        and an allowed end from map_timeline. Returns a job id for job_status."""
        try:
            return crop.crop(map_id, start_beat, end_beat)
        except ApiError as exc:
            raise ToolError(str(exc)) from None
