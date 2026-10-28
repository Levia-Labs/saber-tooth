"""Info.dat fields of a cropped map."""

from dataclasses import replace

from saber_tooth.model import MapInfo

PREVIEW_S = 10.0
PREVIEW_AT = 0.25  # the preview starts a quarter of the way in


def crop_info(info: MapInfo, total_s: float, label: str) -> MapInfo:
    """Song name suffix and a preview that lies inside the new audio of `total_s` seconds."""
    duration = min(info.preview_duration or PREVIEW_S, PREVIEW_S, total_s)
    start = max(0.0, min(total_s * PREVIEW_AT, total_s - duration))
    return replace(
        info,
        song_name=f"{info.song_name} [{label}]",
        preview_start=round(start, 1),
        preview_duration=round(duration, 1),
    )
