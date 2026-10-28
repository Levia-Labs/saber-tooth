import json
import shutil
from pathlib import Path

from saber_tooth.mapio.errors import safe_name
from saber_tooth.model import DIFFICULTIES, RANKS, Beatmap, Difficulty, MapInfo, Wall

FX_KEY = "_fxEventsCollection"
BOX_KEYS = (
    "lightColorEventBoxGroups",
    "lightRotationEventBoxGroups",
    "lightTranslationEventBoxGroups",
    "vfxEventBoxGroups",
)


def strip_custom(value):
    """Recursively drop every customData/_customData key."""
    if isinstance(value, dict):
        drop = ("customData", "_customData")
        return {k: strip_custom(v) for k, v in value.items() if k not in drop}
    if isinstance(value, list):
        return [strip_custom(v) for v in value]
    return value


def _wall_json(w: Wall) -> dict:
    return {"b": w.beat, "x": w.x, "y": w.y, "d": w.duration, "w": w.width, "h": w.height}


def _fx_json(d: Difficulty) -> dict:
    """The fx float/int lists; vfx box groups index into them, so both travel together."""
    fx = d.raw.get(FX_KEY)
    if fx is None:
        return {"vfxEventBoxGroups": [], FX_KEY: {"_fl": [], "_il": []}}
    return {
        "vfxEventBoxGroups": strip_custom(d.raw.get("vfxEventBoxGroups", [])),
        FX_KEY: strip_custom(fx),
    }


def difficulty_json(d: Difficulty) -> dict:
    return {
        "version": "3.3.0",
        "bpmEvents": [{"b": e.beat, "m": e.bpm} for e in d.bpm_events],
        "rotationEvents": [],
        "colorNotes": [
            {"b": n.beat, "x": n.x, "y": n.y, "c": int(n.color), "d": int(n.cut), "a": n.angle}
            for n in d.notes
        ],
        "bombNotes": [{"b": b.beat, "x": b.x, "y": b.y} for b in d.bombs],
        "obstacles": [_wall_json(w) for w in d.walls],
        "sliders": strip_custom(d.raw.get("sliders", [])),
        "burstSliders": strip_custom(d.raw.get("burstSliders", [])),
        "waypoints": [],
        "basicBeatmapEvents": [
            {"b": e.beat, "et": e.type, "i": e.value, "f": e.float_value} for e in d.events
        ],
        "colorBoostBeatmapEvents": [{"b": b, "o": bool(o)} for b, o in d.boosts],
        **{k: strip_custom(d.raw.get(k, [])) for k in BOX_KEYS},
        **_fx_json(d),
        "basicEventTypesWithKeywords": {"d": []},
        "useNormalEventsAsCompatibleEvents": True,
    }


def info_json(info: MapInfo, diffs: list[Difficulty]) -> dict:
    scheme = info.color_scheme
    beatmaps = []
    for d in diffs:
        entry = {
            "_difficulty": d.name,
            "_difficultyRank": RANKS[d.name],
            "_beatmapFilename": f"{d.name}.dat",
            "_noteJumpMovementSpeed": d.njs,
            "_noteJumpStartBeatOffset": d.offset,
            "_environmentNameIdx": 0,
        }
        if scheme:
            entry["_beatmapColorSchemeIdx"] = 0
        beatmaps.append(entry)
    out = {
        "_version": "2.1.0",
        "_songName": info.song_name,
        "_songSubName": info.sub_name,
        "_songAuthorName": info.author,
        "_levelAuthorName": info.mapper,
        "_beatsPerMinute": info.bpm,
        "_songTimeOffset": 0,
        "_shuffle": 0,
        "_shufflePeriod": 0.5,
        "_previewStartTime": info.preview_start,
        "_previewDuration": info.preview_duration,
        "_songFilename": info.song_file,
        "_coverImageFilename": info.cover_file,
        "_environmentName": info.environment,
        "_environmentNames": [info.environment],
        "_difficultyBeatmapSets": [
            {"_beatmapCharacteristicName": "Standard", "_difficultyBeatmaps": beatmaps}
        ],
    }
    if scheme:
        out["_colorSchemes"] = [
            {"useOverride": True, "colorScheme": {"colorSchemeId": scheme.id, **scheme.colors}}
        ]
    return out


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


def copy_asset(copy_from: Path, folder: Path, name: str) -> None:
    """Copy one named file from the source map folder; skips empty names and files outside it."""
    if not name:
        return
    safe_name(name)
    src = (copy_from / name).resolve()
    if copy_from.resolve() in src.parents and src.is_file():
        shutil.copyfile(src, folder / name)


def write_map(beatmap: Beatmap, folder: Path, copy_from: Path | None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    diffs = [beatmap.difficulties[n] for n in DIFFICULTIES if n in beatmap.difficulties]
    for d in diffs:
        _dump(folder / f"{d.name}.dat", difficulty_json(d))
    _dump(folder / "Info.dat", info_json(beatmap.info, diffs))
    if copy_from is not None:
        for name in (beatmap.info.song_file, beatmap.info.cover_file):
            copy_asset(copy_from, folder, name)
