"""HTTP routes for /api/beatsaver/*; the logic lives in beatsaver.py."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from saber_tooth.api.beatsaver import BeatSaverApi, BsHttpError
from saber_tooth.api.core import ApiError


async def _json_body(request: Request) -> object:
    try:
        return await request.json()
    except ValueError:
        raise ApiError(400, "send a JSON body") from None


def register(app: FastAPI, bs: BeatSaverApi) -> None:
    @app.exception_handler(BsHttpError)
    async def _bs_error(_: Request, exc: BsHttpError):
        body: dict = {"error": str(exc)}
        headers = {}
        if exc.retry_after is not None:
            body["retry_after"] = exc.retry_after
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(body, status_code=exc.status, headers=headers)

    def query(request: Request) -> dict[str, str]:
        return dict(request.query_params)

    @app.get("/api/beatsaver/config")
    def config():
        return bs.config()

    @app.get("/api/beatsaver/search")
    def search(request: Request):
        return bs.search(query(request))

    @app.get("/api/beatsaver/maps/{map_id}")
    def bs_map(map_id: str):
        return bs.map(map_id)

    @app.get("/api/beatsaver/playlists/search")
    def playlists_search(request: Request):
        return bs.playlists_search(query(request))

    @app.get("/api/beatsaver/playlists/{playlist_id}")
    def playlist(playlist_id: str, request: Request):
        return bs.playlist(playlist_id, query(request))

    @app.post("/api/beatsaver/download")
    async def download(request: Request):
        return bs.download(await _json_body(request))

    @app.post("/api/beatsaver/playlist-export")
    async def export(request: Request):
        return bs.export(await _json_body(request))

    @app.get("/api/beatsaver/presets")
    def presets():
        return bs.presets.list()

    @app.post("/api/beatsaver/presets")
    async def preset_add(request: Request):
        return bs.preset_add(await _json_body(request))

    @app.delete("/api/beatsaver/presets/{preset_id}")
    def preset_delete(preset_id: str):
        return bs.preset_delete(preset_id)
