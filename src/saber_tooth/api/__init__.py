"""HTTP API: JSON routes for the review UI, plus the static frontend at /."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from saber_tooth.analyser_client import AnalyserClient
from saber_tooth.api.core import Api, ApiError, _error
from saber_tooth.api.hosts import (
    allowed_hosts,
    effective_origin,
    host_allowed,
    peer_trusted,
    trusted_proxies,
)
from saber_tooth.api.upload import _save_upload
from saber_tooth.audio import encode_egg
from saber_tooth.service import ApplyConflict, MapNotFound, MapUnreadable, Service
from saber_tooth.store import Store

WEB = Path(__file__).resolve().parents[1] / "web"


def create_app(service: Service) -> FastAPI:
    app = FastAPI(title="saber-tooth", docs_url=None, redoc_url=None, openapi_url=None)
    api = Api(service)
    app.state.api = api
    hosts = allowed_hosts()
    proxies = trusted_proxies()

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        scheme, host = effective_origin(
            request.headers,
            request.url.scheme,
            peer_trusted(request.client.host if request.client else None, proxies),
        )
        if not host_allowed(host, hosts):
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

    @app.get("/api/maps")
    def maps():
        return api.maps()

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

    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
    return app


def build_service() -> Service:
    """Build the production service from the environment and index the library."""
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
    service.refresh_library()
    return service


_app: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:
    """Build the module-level `app` on first access so importing never touches /levels."""
    global _app
    if name != "app":
        raise AttributeError(name)
    if _app is None:
        _app = create_app(build_service())
    return _app
