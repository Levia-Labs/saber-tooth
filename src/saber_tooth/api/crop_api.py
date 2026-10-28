"""Crop highlight API logic: the timeline and the crop job."""

import math

from saber_tooth.api.core import Api, ApiError
from saber_tooth.crop.errors import CropError


def _beat(value: object, name: str) -> float:
    rule = ApiError(422, f"{name} must be a number of beats, 0 or more")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise rule
    try:
        beat = float(value)
    except (OverflowError, ValueError, TypeError):
        raise rule from None
    if not math.isfinite(beat) or beat < 0:
        raise rule
    return beat


class CropApi:
    """Timeline and crop-job calls over one Api, shared by the REST routes and the MCP tools."""

    def __init__(self, api: Api) -> None:
        self.api = api
        self.service = api.service

    def timeline(self, raw: str) -> dict:
        map_id = self.api.readable_map(raw)
        try:
            return self.service.crop_timeline(map_id)  # type: ignore[attr-defined]
        except CropError as exc:
            raise ApiError(422, str(exc)) from None

    def crop(self, raw: str, start: object, end: object) -> dict:
        map_id = self.api.readable_map(raw)
        if self.api.store.has_active_job(map_id):
            raise ApiError(409, "the map has a queued or running job")
        start_beat, end_beat = _beat(start, "start_beat"), _beat(end, "end_beat")
        try:
            self.service.crop_check(map_id, start_beat, end_beat)  # type: ignore[attr-defined]
        except CropError as exc:
            raise ApiError(422, str(exc)) from None
        run = self.service.crop_map  # type: ignore[attr-defined]
        job = self.api.jobs.submit("crop", run, map_id, start_beat, end_beat, map_id=map_id)
        return {"job": job}
