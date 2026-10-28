# ruff: noqa: F811
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from tests.test_api import MID, client, svc  # noqa: F401

HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}
TOOLS = {
    "list_maps", "get_proposals", "scan_map", "job_status", "approve_proposal",
    "reject_proposal", "apply_map", "fix_map", "generate_from_youtube", "learn_lightshows",
    "beatsaver_search", "beatsaver_download", "map_timeline", "crop_map",
}  # fmt: skip
READ_ONLY = {"list_maps", "get_proposals", "job_status", "beatsaver_search", "map_timeline"}


def rpc(c, method, params=None, ident=1):
    body = {"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}}
    return c.post("/mcp", json=body, headers=HEADERS)


def call(c, name, **args):
    resp = rpc(c, "tools/call", {"name": name, "arguments": args})
    assert resp.status_code == 200
    return resp.json()["result"]


def test_initialize_and_list_tools(client):
    init = rpc(
        client,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "t", "version": "1"},
        },
    )
    assert init.status_code == 200
    assert init.json()["result"]["serverInfo"]["name"] == "saber-tooth"
    tools = {t["name"]: t for t in rpc(client, "tools/list", ident=2).json()["result"]["tools"]}
    assert set(tools) == TOOLS
    for name, tool in tools.items():
        assert tool["annotations"]["readOnlyHint"] is (name in READ_ONLY)
    assert "CustomLevels" in tools["apply_map"]["description"]


def test_list_maps_tool_returns_maps(client):
    result = call(client, "list_maps")
    data = result["structuredContent"]
    assert data["total"] == 1 and data["maps"][0]["id"] == MID
    assert call(client, "list_maps", filter="nomatch-zzz")["structuredContent"]["maps"] == []


def test_scan_tool_returns_job_that_job_status_reads(client):
    job = call(client, "scan_map", map_id=MID)["structuredContent"]["job"]
    status = call(client, "job_status", job_id=job)["structuredContent"]
    assert status["id"] == job and status["kind"] == "scan"


def test_tool_errors_are_reported_not_raised(client):
    result = call(client, "get_proposals", map_id="nope")
    assert result["isError"] is True


def test_youtube_allowlist_applies(client):
    result = call(client, "generate_from_youtube", url="http://evil.example/x")
    assert result["isError"] is True


def test_foreign_host_is_rejected(svc):
    with TestClient(create_app(svc), base_url="http://evil.example") as c:
        assert rpc(c, "tools/list").status_code == 403


def test_rest_routes_unaffected(client):
    assert client.get("/api/maps").status_code == 200
    assert client.get("/api/maps/facets").status_code == 200


def test_map_timeline_tool_returns_the_contract(client):
    data = call(client, "map_timeline", map_id=MID)["structuredContent"]
    assert data["map_id"] == MID and set(data["lengths"]) == {"60", "120"}
    assert data["lengths"]["60"]["enabled"] is False  # the fixture song is 3 s long


def test_crop_map_tool_reports_a_broken_window_as_an_error(client):
    result = call(client, "crop_map", map_id=MID, start_beat=5.0, end_beat=9.0)
    assert result["isError"] is True
    assert "no crop length is available" in result["content"][0]["text"]
