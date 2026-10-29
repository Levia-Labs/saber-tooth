"""HTTP routes for /api/playlists/*; the logic lives in playlists_api.py."""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from saber_tooth.api.core import ApiError
from saber_tooth.api.playlists_api import PlaylistsApi

BPLIST_HEADERS = {"Cache-Control": "no-cache"}


async def _body(request: Request) -> object:
    try:
        return await request.json()
    except ValueError:
        raise ApiError(400, "send a JSON body") from None


def _base(request: Request) -> str:
    return str(request.base_url)


def register(app: FastAPI, pl: PlaylistsApi) -> None:
    @app.get("/api/playlists/config")
    def config():
        return pl.config()

    @app.get("/api/playlists/live/{name}.bplist")
    def live(name: str, request: Request):
        return JSONResponse(pl.live_doc(name, _base(request)), headers=BPLIST_HEADERS)

    @app.get("/api/playlists/picks/jobs/{job_id}")
    def pick_job(job_id: str):
        return pl.picks("job", job_id)

    @app.get("/api/playlists/picks/live/{name}")
    def pick_live(name: str):
        return pl.picks("live", name)

    @app.get("/api/playlists")
    def items(request: Request):
        return pl.listing(_base(request))

    @app.post("/api/playlists")
    async def create(request: Request):
        return pl.save(await _body(request), _base(request))

    @app.post("/api/playlists/from-maps")
    async def from_maps(request: Request):
        return pl.from_maps(await _body(request), _base(request))

    @app.get("/api/playlists/{pid}")
    def one(pid: str, request: Request):
        return pl.get(pid, _base(request))

    @app.post("/api/playlists/{pid}")  # POST as well as PUT: the web client sends GET/POST/DELETE
    @app.put("/api/playlists/{pid}")
    async def update(pid: str, request: Request):
        return pl.save(await _body(request), _base(request), pid)

    @app.delete("/api/playlists/{pid}")
    def remove(pid: str):
        return pl.delete(pid)

    @app.get("/api/playlists/{pid}/cover")
    def cover(pid: str):
        data, ctype = pl.cover(pid)
        return Response(data, media_type=ctype, headers={"Cache-Control": "private, max-age=3600"})

    @app.get("/api/playlists/{pid}/bplist")
    def bplist(pid: str, request: Request):
        return JSONResponse(pl.doc(pid, _base(request)), headers=BPLIST_HEADERS)

    @app.post("/api/playlists/{pid}/export")
    async def export(pid: str, request: Request):
        body = await request.json() if await request.body() else {}
        return pl.export(pid, body, _base(request))
