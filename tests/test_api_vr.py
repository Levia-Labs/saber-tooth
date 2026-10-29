# ruff: noqa: F811
"""GET /api/vr/status, the VR client routes, no MCP tool, and the LAN host check."""

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.api.vr_status import VrStatusClient
from tests.test_api import svc  # noqa: F401
from tests.test_mcp import rpc

AGENT = {
    "os": "windows",
    "runtime": "SteamVR",
    "runtimes": ["SteamVR"],
    "xr_runtime": "SteamVR",
    "worn": True,
}


def injected(answer=AGENT):
    return VrStatusClient(url="http://h/status", native=False, fetch=lambda url, timeout: answer)


def test_status_route_answers_the_clients_status(svc):
    with TestClient(create_app(svc, vr_status=injected()), base_url="http://localhost") as c:
        res = c.get("/api/vr/status")
    assert res.status_code == 200
    assert res.json() == {**AGENT, "source": "agent"}


def test_status_route_with_no_helper_still_answers_200(svc):
    def fetch(url, timeout):
        raise OSError("down")

    client = VrStatusClient(url="http://h/status", native=False, fetch=fetch)
    with TestClient(create_app(svc, vr_status=client), base_url="http://localhost") as c:
        res = c.get("/api/vr/status")
    assert res.status_code == 200 and res.json()["source"] == "none"
    assert res.json()["runtime"] is None and res.json()["runtimes"] == []


def test_other_vr_api_paths_stay_404_json(svc):
    with TestClient(create_app(svc, vr_status=injected()), base_url="http://localhost") as c:
        res = c.get("/api/vr/other")
    assert res.status_code == 404 and res.json() == {"error": "not found"}


def test_status_is_not_an_mcp_tool(svc):
    with TestClient(create_app(svc, vr_status=injected()), base_url="http://localhost") as c:
        tools = rpc(c, "tools/list", ident=2).json()["result"]["tools"]
    assert tools and not [t["name"] for t in tools if "vr" in t["name"].lower()]


@pytest.mark.parametrize("path", ["/vr", "/vr/maps/abc123", "/vr/beatsaver", "/vr/jobs", "/jobs"])
def test_vr_client_routes_serve_the_shell_on_reload(svc, tmp_path, path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<html>shell</html>", encoding="utf-8")
    app = create_app(svc, web=web, vr_status=injected())
    with TestClient(app, base_url="http://localhost") as client:
        res = client.get(path)
    assert res.status_code == 200 and "shell" in res.text


def test_an_unlisted_lan_host_is_refused_with_403(svc, monkeypatch):
    monkeypatch.delenv("SABER_ALLOWED_HOSTS", raising=False)
    app = create_app(svc, vr_status=injected())
    with TestClient(app, base_url="http://192.168.1.50:8100") as client:
        res = client.get("/api/vr/status")
    assert res.status_code == 403 and res.json() == {"error": "host not allowed"}


def test_a_listed_lan_host_is_served(svc, monkeypatch):
    monkeypatch.setenv("SABER_ALLOWED_HOSTS", "192.168.1.50")
    app = create_app(svc, vr_status=injected())
    with TestClient(app, base_url="http://192.168.1.50:8100") as client:
        res = client.get("/api/vr/status")
    assert res.status_code == 200 and res.json()["source"] == "agent"
