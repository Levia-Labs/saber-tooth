"""Bulk map deletion: `POST /api/maps/delete`."""

from fastapi import FastAPI, Request

from saber_tooth.api.core import MAP_ID, Api, ApiError

MAX_IDS = 500


def parse_ids(body: object) -> list[str]:
    raw = body.get("ids") if isinstance(body, dict) else None
    if not isinstance(raw, list) or not raw:
        raise ApiError(400, 'send JSON {"ids": [map ids]}')
    if len(raw) > MAX_IDS:
        raise ApiError(413, f"at most {MAX_IDS} ids per request")
    if not all(isinstance(i, str) and MAP_ID.fullmatch(i) for i in raw):
        raise ApiError(400, "ids must be map ids")
    return list(dict.fromkeys(raw))


def register(app: FastAPI, api: Api) -> None:
    @app.post("/api/maps/delete")
    async def _delete_maps(request: Request):
        try:
            body = await request.json()
        except ValueError:
            raise ApiError(400, 'send JSON {"ids": [map ids]}') from None
        return api.service.delete_maps(parse_ids(body))
