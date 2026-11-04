"""Write a cropped map into a new folder beside the original, never into an existing one."""

import shutil
from dataclasses import replace
from pathlib import Path

from saber_tooth.audio import cut_egg
from saber_tooth.copynames import fixed_name, strip_crop
from saber_tooth.crop.info import crop_info
from saber_tooth.crop.replace import replace_folder
from saber_tooth.crop.shift import Cropped
from saber_tooth.mapio import write_map
from saber_tooth.mapio.errors import safe_name
from saber_tooth.mapio.write import copy_asset
from saber_tooth.safe_fs import LevelsWriter

FADE_IN_S = 0.5


def stage_cropped(
    levels: Path, original: Path, audio: Path, cropped: Cropped, copy: bool = True
) -> tuple[Path, str]:
    """Write the cropped map into a partial folder and return it with the name `<song>
    [saber-tooth]` (numbered when taken, only meant for a swap): Info and difficulty files, the
    cover and the cut song. The partial folder is removed on any failure."""
    info = cropped.beatmap.info
    beatmap = replace(
        cropped.beatmap, info=crop_info(info, cropped.lead_s + cropped.length_s, copy)
    )
    writer = LevelsWriter(levels)
    name = writer.unique_name(fixed_name(strip_crop(original.name)))
    partial = writer.new_folder(name)
    try:
        write_map(beatmap, partial, None)
        copy_asset(original, partial, info.cover_file)
        cut_egg(
            audio,
            partial / safe_name(info.song_file),
            cropped.start_s,
            cropped.length_s,
            cropped.lead_s,
            FADE_IN_S,
            cropped.fade_out_s,
        )
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return partial, name


def write_cropped(levels: Path, original: Path, audio: Path, cropped: Cropped) -> Path:
    """Stage the cropped map and make it the song's one saber-tooth copy: a new
    `<song> [saber-tooth]` folder, or the existing copy overwritten (a copy is cropped in place)."""
    partial, name = stage_cropped(levels, original, audio, cropped)
    try:
        existing = levels / fixed_name(strip_crop(original.name))
        if existing.is_dir():
            return replace_folder(levels, existing, partial)
        return LevelsWriter(levels).commit(partial, name)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
