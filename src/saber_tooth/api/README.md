# api

The FastAPI app: JSON routes for the review UI, with the built frontend in [web](../web) mounted at `/` ([static.py](static.py) sets the cache headers). Routes are described in [api.md](../../../docs/api.md).

1. `__init__.py`: `create_app(service)`, same-origin check, error handlers, lazy module-level `app` built from the environment.
2. `core.py`: `Api` route logic, id validation, proposal views, YouTube URL check.
3. `mcp_tools.py`: `build_mcp(api)`, the MCP tools served at `/mcp` (see [api.md](../../../docs/api.md#mcp)).
4. `library.py`: query validation, item shaping, cover and difficulty lookup with path containment.
5. `web_routes.py`: `/api/maps` page, item and cover routes, `/api/*` 404, SPA routes.
6. `static.py`: `WebFiles`, static files with `immutable` caching for `/assets/*` and `no-cache` otherwise.
7. `upload.py`: streams multipart uploads to a temp file under `DATA_DIR/uploads`, enforcing `MAX_UPLOAD_MB`.
8. `beatsaver.py`, `beatsaver_routes.py`: BeatSaver search, download, playlist and preset routes (see [api.md](../../../docs/api.md#beatsaver)); `mcp_tools.py` adds `beatsaver_search` and `beatsaver_download`.
9. `crop_api.py`, `crop_routes.py`: `CropApi` (timeline and crop job, 409 before 422) and the `GET /timeline` and `POST /crop` routes (see [api.md](../../../docs/api.md#routes)).

Tests: `task st:test -- tests/test_api.py` or `tests/test_api_library.py` or `tests/test_mcp.py`, `tests/test_web_cache.py`.
