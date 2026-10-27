"""HTTP API: JSON routes for the review UI, plus the static frontend at /."""

import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from mcp.server.transport_security import TransportSecuritySettings

from saber_tooth.analyser_client import AnalyserClient
from saber_tooth.api.core import Api, ApiError, _error
from saber_tooth.api.hosts import (
    allowed_hosts,
    effective_origin,
    host_allowed,
    peer_trusted,
    trusted_proxies,
)
from saber_tooth.api.mcp_tools import build_mcp
from saber_tooth.api.static import WebFiles
from saber_tooth.api.upload import _save_upload
from saber_tooth.api.web_routes import register as register_web_routes
from saber_tooth.audio import encode_egg
from saber_tooth.service import ApplyConflict, MapNotFound, MapUnreadable, Service
from saber_tooth.store import Store

log = logging.getLogger(__name__)
WEB = Path(__file__).resolve().parents[1] / "web"


def create_app(service: Service, web: Path = WEB, warm: bool = False) -> FastAPI:
    """Build the app; `warm` runs the first library refresh in a background thread."""
    api = Api(service)
    # The SDK's own Host check is off: same_origin below already covers /mcp, and honours
    # SABER_ALLOWED_HOSTS and trusted proxies, which the SDK list cannot.
    mcp_app = build_mcp(api).streamable_http_app(
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if warm:
            threading.Thread(
                target=_warm, args=(service,), name="library-warm", daemon=True
            ).start()
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app = FastAPI(
        title="saber-tooth", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
    )
    app.state.api = api
    hosts = allowed_hosts()
    proxies = trusted_proxies()

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        trusted = peer_trusted(request.client.host if request.client else None, proxies)
        scheme, host = effective_origin(request.headers, request.url.scheme, trusted)
        direct_ok = not trusted or host_allowed(request.headers.get("host"), hosts)
        if not direct_ok or not host_allowed(host, hosts):
            return _error(403, "host not allowed")
        origin = request.headers.get("origin")
        here = f"{scheme}://{host}".lower()
        unsafe = request.method not in ("GET", "HEAD", "OPTIONS")
        if unsafe and origin is not None and origin.lower().rstrip("/") != here:
            return _error(403, "cross-origin request refused")
        return await call_next(request)

    @app.exception_handler(MapNotFound)
    async def _not_found(_: Request, exc: MapNotFound):
        return _error(404, str(exc))

    @app.exception_handler(MapUnreadable)
    @app.exception_handler(ApplyConflict)
    async def _conflict(_: Request, exc: Exception):
        return _error(409, str(exc))

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return _error(exc.status, str(exc))

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # The library, cover and SPA routes are registered after the JSON routes below so the
    # catch-all /api/* 404 never shadows them.
    @app.post("/api/maps/{map_id}/scan")
    def scan(map_id: str):
        return api.scan(map_id)

    @app.get("/api/maps/{map_id}/proposals")
    def proposals(map_id: str):
        return api.proposals(map_id)

    @app.post("/api/proposals/{pid}/approve")
    def approve(pid: str):
        return api.set_status(pid, "approved")

    @app.post("/api/proposals/{pid}/reject")
    def reject(pid: str):
        return api.set_status(pid, "rejected")

    @app.post("/api/maps/{map_id}/approve-all")
    def approve_all(map_id: str):
        return api.approve_all(map_id)

    @app.post("/api/maps/{map_id}/apply")
    def apply(map_id: str):
        return api.apply(map_id)

    @app.post("/api/generate")
    async def generate(request: Request):
        ctype = request.headers.get("content-type", "")
        if ctype.startswith("multipart/form-data"):
            return api.generate_file(await _save_upload(request, service.data))
        try:
            body = await request.json()
        except ValueError:
            raise ApiError(400, "send JSON {\"url\"} or a multipart 'file'") from None
        return api.generate_url(body.get("url") if isinstance(body, dict) else None)

    @app.post("/api/lightshow/learn")
    def learn():
        return api.learn()

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return api.job(job_id)

    register_web_routes(app, api, web)
    # The /mcp route sits behind the same_origin middleware above, which is the Host check.
    app.router.routes.extend(mcp_app.routes)
    app.mount("/", WebFiles(directory=web, html=True), name="web")
    return app


def build_service() -> Service:
    """Build the production service from the environment; the library is indexed by `warm`."""
    data = Path(os.environ.get("DATA_DIR", "/data"))
    data.mkdir(parents=True, exist_ok=True)
    client = AnalyserClient(
        os.environ.get("ANALYSER_URL", "http://beat-analyser:8000"),
        Path(os.environ.get("ANALYSER_UPLOADS", "/analyser")),
    )
    service = Service(
        Path(os.environ.get("LEVELS_DIR", "/levels")),
        data,
        Store(data / "saber-tooth.db"),
        client,
        encode_egg,
    )
    return service


def _warm(service: Service) -> None:
    try:
        service.refresh_if_changed()
    except Exception:  # a failed warm-up must not kill the server; /api/maps retries
        log.exception("initial library refresh failed")


_app: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:
    """Build the module-level `app` on first access so importing never touches /levels."""
    global _app
    if name != "app":
        raise AttributeError(name)
    if _app is None:
        _app = create_app(build_service(), warm=True)
    return _app
