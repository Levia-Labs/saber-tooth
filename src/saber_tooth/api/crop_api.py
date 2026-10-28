"""Crop highlight API logic: the timeline and the crop job."""

import math
from typing import Any

from saber_tooth.api.core import Api, ApiError
from saber_tooth.crop.errors import CropError
from saber_tooth.crop.timeline import MIN_LENGTH_S

_MISSING: Any = object()
_PAIR_RULE = "send either start_beat and end_beat or start_s and end_s"


def _number(value: object, name: str, unit: str) -> float:
    rule = ApiError(422, f"{name} must be a number of {unit}, 0 or more")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise rule
    try:
        number = float(value)
    except (OverflowError, ValueError, TypeError):
        raise rule from None
    if not math.isfinite(number) or number < 0:
        raise rule
    return number


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

    def crop(
        self,
        raw: str,
        start_beat: object = _MISSING,
        end_beat: object = _MISSING,
        replace: object = False,
        start_s: object = _MISSING,
        end_s: object = _MISSING,
    ) -> dict:
        """Queue a crop; the window is a beat pair or a seconds pair, never both."""
        map_id = self.api.readable_map(raw)
        if self.api.store.has_active_job(map_id):
            raise ApiError(409, "the map has a queued or running job")
        beats = start_beat is not _MISSING or end_beat is not _MISSING
        seconds = start_s is not _MISSING or end_s is not _MISSING
        if beats == seconds:
            raise ApiError(422, _PAIR_RULE)
        pair = ("start_s", "end_s", "seconds") if seconds else ("start_beat", "end_beat", "beats")
        given = (start_s, end_s) if seconds else (start_beat, end_beat)
        start, end = (
            _number(None if v is _MISSING else v, name, pair[2])
            for v, name in zip(given, pair[:2], strict=True)
        )
        try:
            if seconds:
                if start < end and end - start < MIN_LENGTH_S - 1e-6:  # judged on the seconds sent
                    raise CropError("the window must be at least 1 second long")
                start, end = self.service.crop_beats(map_id, start, end)  # type: ignore[attr-defined]
            self.service.crop_check(map_id, start, end)  # type: ignore[attr-defined]
        except CropError as exc:
            raise ApiError(422, str(exc)) from None
        if not isinstance(replace, bool):
            raise ApiError(422, "replace must be true or false")
        run = self.service.crop_map  # type: ignore[attr-defined]
        args = (map_id, start, end, *((True,) if replace else ()))
        job = self.api.jobs.submit("crop", run, *args, map_id=map_id)
        return {"job": job}
