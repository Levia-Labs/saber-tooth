"""MCP tools: thin wrappers over the same Api calls the REST routes use."""

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from saber_tooth.api.core import Api

MAX_MAPS = 200
MAX_PROPOSALS = 200

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
SAFE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
JOB = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
WEB = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)


def build_mcp(api: Api) -> MCPServer:
    mcp = MCPServer("saber-tooth", instructions="Review and fix Beat Saber custom levels.")

    @mcp.tool(annotations=READ)
    def list_maps(filter: str = "") -> dict[str, Any]:
        """List indexed maps (id, folder, title, mapper, error counts); filter is a substring."""
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

    @mcp.tool(annotations=WEB)
    def generate_from_youtube(url: str) -> dict[str, Any]:
        """Generate a new map from a YouTube URL (youtube.com or youtu.be); returns a job id."""
        return api.generate_url(url)

    @mcp.tool(annotations=JOB)
    def learn_lightshows() -> dict[str, Any]:
        """Learn lighting patterns from the indexed library; returns a job id."""
        return api.learn()

    return mcp
