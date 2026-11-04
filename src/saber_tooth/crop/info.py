"""Info.dat fields of a cropped map."""

from dataclasses import replace

from saber_tooth.copynames import fixed_name, strip_crop
from saber_tooth.model import MapInfo

PREVIEW_S = 10.0
PREVIEW_AT = 0.25  # the preview starts a quarter of the way in


def crop_info(info: MapInfo, total_s: float, copy: bool = True) -> MapInfo:
    """Song name with the saber-tooth suffix, and a preview inside the new audio of `total_s`."""
    duration = min(info.preview_duration or PREVIEW_S, PREVIEW_S, total_s)
    start = max(0.0, min(total_s * PREVIEW_AT, total_s - duration))
    return replace(
        info,
        song_name=fixed_name(strip_crop(info.song_name)) if copy else strip_crop(info.song_name),
        preview_start=round(start, 1),
        preview_duration=round(duration, 1),
    )
