# Task 7: `GET /api/vr/status` route, SPA routes and the LAN host check

A new router module, built the way `crop_routes.py` is: `register(app, client)` called from `create_app` before the web routes, so the catch-all `/api/*` 404 never shadows it. `create_app` takes an optional `vr_status` so tests inject a client. The route is not exposed through MCP (the existing `TOOLS` set in `tests/test_mcp.py` already pins the tool list; this task adds a check that no tool name mentions VR). The three VR screens are client routes, so `/vr`, `/vr/maps/{id}` and `/vr/beatsaver` answer with `index.html` on reload. The LAN case is pinned as it behaves today: an unlisted host is refused by `same_origin` in `api/__init__.py` with 403 `{"error": "host not allowed"}`, not the 400 the spec text names (finding in the index).

**Files:**

- Create: `src/saber_tooth/api/vr_routes.py`
- Modify: `src/saber_tooth/api/__init__.py` (two imports, one parameter, one call)
- Modify: `src/saber_tooth/api/web_routes.py` (three `@app.get` decorators on `spa`)
- Modify: `src/saber_tooth/api/README.md` (append one list item)
- Test: `tests/test_api_vr.py`

**Interfaces:**

Consumes: `VrStatusClient` (Task 6), `register_crop` pattern (`api/crop_routes.py`), `svc` fixture and `rpc` helper (`tests/test_api.py`, `tests/test_mcp.py`).

Produces:

1. `vr_routes.register(app: FastAPI, client: VrStatusClient) -> None`: `GET /api/vr/status` answering `client.status()`.
2. `create_app(service, web=WEB, warm=False, bs_client=None, playlists_dir=None, vr_status: VrStatusClient | None = None) -> FastAPI`.
3. SPA routes `/vr`, `/vr/maps/{map_id}`, `/vr/beatsaver` serving `web/index.html`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_api_vr.py`:

```python
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


@pytest.mark.parametrize("path", ["/vr", "/vr/maps/abc123", "/vr/beatsaver"])
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
```

- [ ] **Step 2: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_api_vr.py`
Expected: FAIL: `TypeError: create_app() got an unexpected keyword argument 'vr_status'`.

- [ ] **Step 3: Implement**

Create `src/saber_tooth/api/vr_routes.py`:

```python
"""HTTP route for the VR runtime status; the logic lives in vr_status.py."""

from fastapi import FastAPI

from saber_tooth.api.vr_status import VrStatusClient


def register(app: FastAPI, client: VrStatusClient) -> None:
    @app.get("/api/vr/status")
    def vr_status():
        return client.status()
```

In `src/saber_tooth/api/__init__.py`, add these two imports between `from saber_tooth.api.upload import _save_upload` and `from saber_tooth.api.web_routes import register as register_web_routes`:

```python
from saber_tooth.api.vr_routes import register as register_vr
from saber_tooth.api.vr_status import VrStatusClient
```

Change the signature and docstring of `create_app`:

```python
    bs_client: BeatSaverClient | None = None,
    playlists_dir: Path | None = None,
    vr_status: VrStatusClient | None = None,
) -> FastAPI:
    """Build the app; `warm` runs the first library refresh in a background thread.

    `bs_client` and `playlists_dir` (default: env PLAYLISTS_DIR) configure the BeatSaver routes;
    `vr_status` (default: built from env VR_AGENT_URL) answers /api/vr/status.
    """
```

Add after `register_crop(app, crop_api)`:

```python
    register_vr(app, vr_status or VrStatusClient())
```

In `src/saber_tooth/api/web_routes.py`, add three decorators above `def spa(`:

```python
    @app.get("/vr", include_in_schema=False)
    @app.get("/vr/maps/{map_id}", include_in_schema=False)
    @app.get("/vr/beatsaver", include_in_schema=False)
```

Append to `src/saber_tooth/api/README.md` after item 9:

```markdown
10. `vr_status.py`, `vr_routes.py`: `VrStatusClient` (host helper over HTTP with a 300 ms timeout and a 2 s cache, or an in-process probe) and the `GET /api/vr/status` route; not an MCP tool.
```

- [ ] **Step 4: Run it to see it pass**

Run: `rtk proxy uv run pytest -q tests/test_api_vr.py tests/test_api_spa_routes.py tests/test_mcp.py`
Expected: PASS (the VR file adds 9 tests).

- [ ] **Step 5: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): GET /api/vr/status route and VR client routes" src/saber_tooth/api/vr_routes.py src/saber_tooth/api/__init__.py src/saber_tooth/api/web_routes.py src/saber_tooth/api/README.md tests/test_api_vr.py`
