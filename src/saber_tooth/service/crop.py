"""Service side of the crop highlight: the timeline, the window check and the crop job."""

import logging
import shutil
from pathlib import Path

from saber_tooth.crop.errors import CropError
from saber_tooth.crop.phrases import hardest
from saber_tooth.crop.replace import replace_folder
from saber_tooth.crop.shift import crop_beatmap
from saber_tooth.crop.timeline import (
    Timeline,
    build_timeline,
    resolve_window,
    timeline_dict,
    window_label,
)
from saber_tooth.crop.write import stage_cropped, write_cropped
from saber_tooth.mapio import load_map
from saber_tooth.model import Beatmap
from saber_tooth.service.copyscan import store_copy_scan
from saber_tooth.service.duration import audio_path, folder_duration
from saber_tooth.service.util import checkpoint, map_id_for
from saber_tooth.service.verify import stored_analysis

log = logging.getLogger(__name__)


def _timeline(svc, map_id: str) -> tuple[Path, Beatmap, Timeline]:
    folder = svc._folder(map_id)
    beatmap = svc._load(folder)
    hardest(beatmap)  # NoNotes first: a map with no Standard notes has no length either
    duration = folder_duration(folder, beatmap)
    if duration is None:
        raise CropError("the song length is unknown")
    analysis = stored_analysis(svc.uploads, svc.store.scan_info(map_id))
    return folder, beatmap, build_timeline(beatmap, duration, analysis)


def crop_timeline(svc, map_id: str) -> dict:
    """NPS per difficulty, sections and the 1 and 2 minute plans for one map."""
    return timeline_dict(_timeline(svc, map_id)[2], map_id)


def crop_check(svc, map_id: str, start_beat: float, end_beat: float) -> None:
    """Raise InvalidWindow when the pair breaks a window rule; used before a job is queued."""
    resolve_window(_timeline(svc, map_id)[2], start_beat, end_beat)


def crop_beats(svc, map_id: str, start_s: float, end_s: float) -> tuple[float, float]:
    """The beat pair for a seconds pair, converted with the map's own tempo changes."""
    timing = _timeline(svc, map_id)[2].timing
    return timing.to_beats(start_s), timing.to_beats(end_s)


def _replace(
    svc, map_id: str, folder: Path, audio: Path, cropped, label: str, progress=None
) -> Path:
    """Stage the crop, check it reads back, then swap it in for the original folder."""
    partial, _ = stage_cropped(svc.levels, folder, audio, cropped, label)
    try:
        load_map(partial)
        checkpoint(progress)  # the staged copy goes; the original is still untouched
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    target = replace_folder(svc.levels, folder, partial)
    svc.store.reset_map(map_id)
    return target


def crop_map(
    svc,
    map_id: str,
    start_beat: float,
    end_beat: float,
    replace: bool = False,
    progress=None,
) -> dict:
    """Crop a map into a new `<map> [label]` folder; the original is never changed.

    With `replace` the cropped map takes the original folder's place instead and the map's store
    rows are reset."""
    folder, beatmap, tl = _timeline(svc, map_id)
    win = resolve_window(tl, start_beat, end_beat)
    audio = audio_path(folder, beatmap.info.song_file)
    if audio is None:
        raise CropError("the map has no readable song file")
    label = window_label(tl, win.length_s)
    checkpoint(progress, "cropping the map")
    cropped = crop_beatmap(beatmap, tl.timing, win.start_beat, win.end_beat)
    checkpoint(progress, "writing the cropped map")  # last stop before anything is written
    if replace:
        target = _replace(svc, map_id, folder, audio, cropped, label, progress)
    else:
        target = write_cropped(svc.levels, folder, audio, cropped, label)
    store_copy_scan(svc, target.name, cropped.beatmap, None)  # the analysis is on the old time base
    try:
        svc.refresh_library()
    except Exception:
        log.exception("library refresh failed after cropping %s", map_id)
    return {
        "map_id": map_id,
        **({"replaced": True} if replace else {}),
        "folder": target.name,
        "cropped_id": map_id_for(target.name),
        "label": label,
        "start_beat": win.start_beat,
        "end_beat": win.end_beat,
        "length_s": win.length_s,
    }
