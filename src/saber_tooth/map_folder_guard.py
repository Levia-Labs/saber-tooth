"""Strict deletability check: only a genuine Beat Saber map folder may ever be removed."""

import json
import os
import stat
from pathlib import Path

MAX_FILES = 64
MAX_BYTES = 300 * 1024 * 1024
ALLOWED_EXT = frozenset({".dat", ".egg", ".ogg", ".wav", ".png", ".jpg", ".jpeg"})
INFO_NAMES = ("Info.dat", "info.dat")
EXTRA_OK = frozenset({"bpminfo.dat"})
LIST_CAP = 5
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _is_reparse(path: Path) -> bool:
    try:
        st = path.lstat()
    except OSError:
        return True
    if stat.S_ISLNK(st.st_mode) or path.is_symlink():
        return True
    if os.path.isjunction(path):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & _REPARSE)


def _names(items: list[str]) -> str:
    shown = ", ".join(sorted(items)[:LIST_CAP])
    return shown + (f" (+{len(items) - LIST_CAP} more)" if len(items) > LIST_CAP else "")


def _location(folder: Path, root: Path) -> list[str]:
    reasons: list[str] = []
    name = folder.name
    if not name or name in (".", "..") or "/" in name or "\\" in name or name.startswith("."):
        reasons.append(f"unsafe folder name: {name!r}")
    if _is_reparse(folder):
        reasons.append("folder is a symlink, junction or reparse point")
    if not folder.is_dir():
        reasons.append("folder is not a directory")
        return reasons
    try:
        rroot = root.resolve(strict=True)
        rfolder = folder.resolve(strict=True)
    except OSError:
        return [*reasons, "folder or levels root cannot be resolved"]
    if rfolder == rroot:
        reasons.append("target is the levels root")
    elif rfolder.parent != rroot:
        reasons.append("folder is not a direct child of the levels root")
    return reasons


def _scan(folder: Path) -> tuple[dict[str, Path], list[str]]:
    """Return files by name and shape refusals (subdirs, links, count, size)."""
    files: dict[str, Path] = {}
    reasons: list[str] = []
    bad: list[str] = []
    total = 0
    with os.scandir(folder) as it:
        for entry in it:
            path = Path(entry.path)
            if _is_reparse(path) or entry.is_dir(follow_symlinks=False):
                bad.append(f"{entry.name}/")
                continue
            if not entry.is_file(follow_symlinks=False):
                bad.append(entry.name)
                continue
            st = path.lstat()
            if st.st_nlink > 1:
                bad.append(f"{entry.name} (hardlink)")
                continue
            total += st.st_size
            files[entry.name] = path
    if bad:
        reasons.append(f"non-regular entries: {_names(bad)}")
    if len(files) > MAX_FILES:
        reasons.append(f"more than {MAX_FILES} files")
    if total > MAX_BYTES:
        reasons.append(f"larger than {MAX_BYTES // (1024 * 1024)} MB")
    return files, reasons


def _str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _refs_v2(info: dict) -> tuple[str | None, set[str], int] | None:
    sets = info.get("_difficultyBeatmapSets")
    if not (
        isinstance(info.get("_version"), str)
        and _str(info.get("_songName"))
        and _str(info.get("_songFilename"))
        and isinstance(sets, list)
    ):
        return None
    refs: set[str] = set()
    count = 0
    for bset in sets:
        for diff in bset.get("_difficultyBeatmaps", []) if isinstance(bset, dict) else []:
            count += 1
            refs.add(_str(diff.get("_beatmapFilename")) or "" if isinstance(diff, dict) else "")
    refs.add(info["_songFilename"])
    cover = _str(info.get("_coverImageFilename"))
    if cover:
        refs.add(cover)
    return cover, refs, count


def _refs_v4(info: dict) -> tuple[str | None, set[str], int] | None:
    audio, diffs = info.get("audio"), info.get("difficultyBeatmaps")
    if not (
        isinstance(info.get("version"), str)
        and isinstance(info.get("song"), dict)
        and isinstance(audio, dict)
        and _str(audio.get("songFilename"))
        and isinstance(diffs, list)
    ):
        return None
    refs = {audio["songFilename"]}
    for key in ("audioDataFilename",):
        if _str(audio.get(key)):
            refs.add(audio[key])
    cover = _str(info.get("coverImageFilename"))
    if cover:
        refs.add(cover)
    for diff in diffs:
        if not isinstance(diff, dict):
            refs.add("")
            continue
        refs.add(_str(diff.get("beatmapDataFilename")) or "")
        if "lightshowDataFilename" in diff:
            refs.add(_str(diff["lightshowDataFilename"]) or "")
    return cover, refs, len(diffs)


def _info_refs(files: dict[str, Path]) -> tuple[set[str], list[str]]:
    present = [n for n in files if n in INFO_NAMES]
    if len(present) != 1:
        return set(), [f"expected exactly one Info.dat, found {len(present)}"]
    try:
        info = json.loads(files[present[0]].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set(), ["Info.dat is not UTF-8 JSON"]
    if not isinstance(info, dict):
        return set(), ["Info.dat is not a v2 or v4 info"]
    parsed = _refs_v4(info) if "version" in info else _refs_v2(info)
    if parsed is None:
        return set(), ["Info.dat is not a v2 or v4 info"]
    _, refs, count = parsed
    if count < 1:
        return set(), ["Info.dat lists no difficulty"]
    lower = {n.lower() for n in files}
    missing = [r for r in refs if r.lower() not in lower]
    if missing:
        names = _names([m or "<empty name>" for m in missing])
        return set(), [f"referenced files missing: {names}"]
    return {r.lower() for r in refs}, []


def check_map_folder(folder: Path, levels_root: Path, map_id: str | None = None) -> list[str]:
    """Refusal reasons for deleting `folder`; an empty list means it is a deletable map folder."""
    reasons = _location(folder, levels_root)
    if reasons and not folder.is_dir():
        return reasons
    try:
        files, shape = _scan(folder)
    except OSError:
        return [*reasons, "folder cannot be listed"]
    reasons += shape
    foreign = [n for n in files if Path(n).suffix.lower() not in ALLOWED_EXT]
    if foreign:
        reasons.append(f"disallowed extensions: {_names(foreign)}")
    refs, info_reasons = _info_refs(files)
    reasons += info_reasons
    if not info_reasons:
        extra = [
            n
            for n in files
            if n not in INFO_NAMES and n.lower() not in refs and n.lower() not in EXTRA_OK
        ]
        if extra:
            reasons.append(f"unreferenced files: {_names(extra)}")
    if map_id is not None:
        from saber_tooth.service.util import map_id_for

        if map_id_for(folder.name) != map_id:
            reasons.append("folder name does not match the map id")
    return reasons
