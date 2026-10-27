import json
from pathlib import Path

from saber_tooth.mapio.errors import MapParseError, safe_name
from saber_tooth.mapio.read_v2 import read_v2
from saber_tooth.mapio.read_v3 import read_v3
from saber_tooth.mapio.read_v4 import read_v4
from saber_tooth.mapio.tempo_regions import V2_KEYS, V4_KEYS, merge_events, regions_to_events
from saber_tooth.model import DIFFICULTIES, Beatmap, ColorScheme, Difficulty, MapInfo
from saber_tooth.timing import Timing

COLOR_KEYS = (
    "saberAColor",
    "saberBColor",
    "environmentColor0",
    "environmentColor1",
    "environmentColor0Boost",
    "environmentColor1Boost",
    "obstaclesColor",
)


def _find_ci(folder: Path, filename: str) -> Path | None:
    want = filename.lower()
    try:
        for p in folder.iterdir():
            if p.name.lower() == want:
                return p
    except OSError as exc:
        raise MapParseError(f"cannot list {folder}: {exc}") from exc
    return None


def find_info(folder: Path) -> Path:
    found = _find_ci(folder, "info.dat")
    if found is None:
        raise MapParseError(f"no info.dat in {folder}")
    return found


def difficulty_path(folder: Path, filename: str) -> Path:
    found = _find_ci(folder, safe_name(filename))
    if found is None:
        raise MapParseError(f"missing difficulty file {filename} in {folder}")
    return found


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MapParseError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise MapParseError(f"{path.name} is not a JSON object")
    return data


def _region_events(folder: Path, filename: str, keys: tuple[str, ...], bpm: float) -> list:
    path = _find_ci(folder, safe_name(filename))
    if path is None:
        return []
    return regions_to_events(_read_json(path), keys, bpm)


def _hex_color(text: str) -> dict[str, float]:
    text = text.lstrip("#").ljust(8, "f")
    r, g, b, a = (int(text[i : i + 2], 16) / 255 for i in (0, 2, 4, 6))
    return {"r": r, "g": g, "b": b, "a": a}


def _scheme_v2(info: dict, idx: int | None) -> ColorScheme | None:
    schemes = info.get("_colorSchemes") or []
    if idx is None or not 0 <= idx < len(schemes) or not schemes[idx].get("useOverride"):
        return None
    cs = schemes[idx]["colorScheme"]
    colors = {k: cs[k] for k in COLOR_KEYS if k in cs}
    return ColorScheme(str(cs.get("colorSchemeId", "")), colors)


def _scheme_v4(info: dict, idx: int | None) -> ColorScheme | None:
    schemes = info.get("colorSchemes") or []
    if idx is None or not 0 <= idx < len(schemes) or not schemes[idx].get("useOverride", True):
        return None
    cs = schemes[idx]
    colors = {k: _hex_color(v) for k, v in cs.items() if k in COLOR_KEYS and isinstance(v, str)}
    return ColorScheme(str(cs.get("colorSchemeName", "")), colors)


def _load_diff_file(path: Path, entry: dict, folder: Path) -> Difficulty:
    data = _read_json(path)
    version = str(data.get("version", ""))
    args = (entry["name"], entry["njs"], entry["offset"])
    if version.startswith("4."):
        show = None
        if entry.get("lightshow"):
            show = _read_json(difficulty_path(folder, entry["lightshow"]))
        return read_v4(data, show, *args, path.name)
    if version.startswith("3."):
        return read_v3(data, *args, path.name)
    return read_v2(data, *args, path.name)


def _opt_name(name: object) -> str:
    return safe_name(name) if name else ""


def _entries_v2(info: dict) -> list[dict]:
    for s in info["_difficultyBeatmapSets"]:
        if s.get("_beatmapCharacteristicName") == "Standard":
            return [
                {
                    "name": b["_difficulty"],
                    "file": safe_name(b["_beatmapFilename"]),
                    "njs": float(b.get("_noteJumpMovementSpeed", 16)),
                    "offset": float(b.get("_noteJumpStartBeatOffset", 0)),
                    "scheme": b.get("_beatmapColorSchemeIdx"),
                }
                for b in s["_difficultyBeatmaps"]
            ]
    return []


def _entries_v4(info: dict) -> list[dict]:
    return [
        {
            "name": b["difficulty"],
            "file": safe_name(b["beatmapDataFilename"]),
            "lightshow": _opt_name(b.get("lightshowDataFilename")),
            "njs": float(b.get("noteJumpMovementSpeed", 16)),
            "offset": float(b.get("noteJumpStartBeatOffset", 0)),
            "scheme": b.get("beatmapColorSchemeIdx"),
        }
        for b in info["difficultyBeatmaps"]
        if b.get("characteristic") == "Standard"
    ]


def _mapinfo_v4(info: dict, scheme_idx: int | None) -> MapInfo:
    song, audio = info["song"], info["audio"]
    authors = [b.get("beatmapAuthors", {}) for b in info["difficultyBeatmaps"]]
    mappers = [m for a in authors for m in a.get("mappers", [])]
    envs = info.get("environmentNames") or [""]
    return MapInfo(
        song_name=song["title"],
        sub_name=song.get("subTitle", ""),
        author=song.get("author", ""),
        mapper=mappers[0] if mappers else "",
        bpm=float(audio["bpm"]),
        song_file=safe_name(audio["songFilename"]),
        cover_file=_opt_name(info.get("coverImageFilename", "")),
        preview_start=float(audio.get("previewStartTime", 0)),
        preview_duration=float(audio.get("previewDuration", 10)),
        environment=envs[0],
        color_scheme=_scheme_v4(info, scheme_idx),
    )


def _mapinfo_v2(info: dict, scheme_idx: int | None) -> MapInfo:
    envs = info.get("_environmentNames") or []
    return MapInfo(
        song_name=info["_songName"],
        sub_name=info.get("_songSubName", ""),
        author=info.get("_songAuthorName", ""),
        mapper=info.get("_levelAuthorName", ""),
        bpm=float(info["_beatsPerMinute"]),
        song_file=safe_name(info["_songFilename"]),
        cover_file=_opt_name(info.get("_coverImageFilename", "")),
        preview_start=float(info.get("_previewStartTime", 0)),
        preview_duration=float(info.get("_previewDuration", 10)),
        environment=info.get("_environmentName") or (envs[0] if envs else ""),
        color_scheme=_scheme_v2(info, scheme_idx),
    )


def load_map(folder: Path) -> Beatmap:
    info = _read_json(find_info(folder))
    v4 = str(info.get("version", "")).startswith("4.")
    try:
        entries = _entries_v4(info) if v4 else _entries_v2(info)
        diffs: dict[str, Difficulty] = {}
        for e in entries:
            if e["name"] in DIFFICULTIES:
                path = difficulty_path(folder, e["file"])
                diffs[e["name"]] = _load_diff_file(path, e, folder)
        idx = next((e["scheme"] for e in entries if e["scheme"] is not None), None)
        meta = _mapinfo_v4(info, idx) if v4 else _mapinfo_v2(info, idx)
        if v4:
            name = info.get("audio", {}).get("audioDataFilename")
            extra = _region_events(folder, name, V4_KEYS, meta.bpm) if name else []
        else:
            extra = _region_events(folder, "BPMInfo.dat", V2_KEYS, meta.bpm)
        for d in diffs.values():
            if extra and (v4 or not d.bpm_events):
                d.bpm_events = merge_events(d.bpm_events, extra)
            Timing(meta.bpm, d.bpm_events)
    except MapParseError:
        raise
    except Exception as exc:  # any malformed input must surface as a parse error
        raise MapParseError(f"bad map in {folder}: {exc!r}") from exc
    return Beatmap(meta, diffs, folder.name)
