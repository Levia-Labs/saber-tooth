"""HTTP routes for the crop highlight; the logic lives in crop_api.py."""

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool

from saber_tooth.api.core import ApiError
from saber_tooth.api.crop_api import CropApi


def register(app: FastAPI, crop: CropApi) -> None:
    @app.get("/api/maps/{map_id}/timeline")
    def timeline(map_id: str):
        return crop.timeline(map_id)

    @app.post("/api/maps/{map_id}/crop")
    async def start_crop(map_id: str, request: Request):
        try:
            body = await request.json()
        except ValueError:
            raise ApiError(400, 'send JSON {"start_beat", "end_beat"}') from None
        fields = body if isinstance(body, dict) else {}
        return await run_in_threadpool(
            crop.crop, map_id, fields.get("start_beat"), fields.get("end_beat")
        )
