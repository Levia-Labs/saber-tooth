"""SongCore's level hash: SHA1 over the level's files, uppercase hex.

v2/v3 Info.dat: its bytes, then every `_difficultyBeatmapSets[*]._difficultyBeatmaps[*]
._beatmapFilename` file in listed order, all characteristics.

v4 Info.dat (SongCore ComputeCustomLevelHash): the Info.dat JSON text as UTF-8, then the file
named by `audio.audioDataFilename`, then for each `difficultyBeatmaps` entry in array order its
`beatmapDataFilename` and its `lightshowDataFilename`.

Missing files are skipped and a file listed twice is hashed twice, as SongCore does. Generated
and fixed maps have no BeatSaver hash, so playlists use this one.
"""

import hashlib
import json
import threading
from pathlib import Path

Stamp = tuple[tuple[str, int, int], ...]
_BAD = "/\\:\x00"


def _find(folder: Path, name: str) -> Path | None:
    want = name.lower()
    try:
        for p in folder.iterdir():
            if p.name.lower() == want and p.is_file():
                return p
    except OSError:
        return None
    return None


def _plain(n: object) -> str | None:
    ok = isinstance(n, str) and n not in ("", ".", "..") and not any(c in n for c in _BAD)
    return n if ok and isinstance(n, str) else None


def _info(raw: bytes) -> dict:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _is_v4(data: dict) -> bool:
    return isinstance(data.get("difficultyBeatmaps"), list)


def _listed(data: dict) -> list[str | None]:
    """File names in hashing order, after Info.dat."""
    names: list[object] = []
    if _is_v4(data):
        audio = data.get("audio")
        names.append(audio.get("audioDataFilename") if isinstance(audio, dict) else None)
        for r in data["difficultyBeatmaps"]:
            if isinstance(r, dict):
                names += [r.get("beatmapDataFilename"), r.get("lightshowDataFilename")]
        return [_plain(n) for n in names]
    sets = data.get("_difficultyBeatmapSets")
    for s in sets if isinstance(sets, list) else []:
        rows = s.get("_difficultyBeatmaps") if isinstance(s, dict) else None
        names += [r.get("_beatmapFilename") for r in rows or [] if isinstance(r, dict)]
    return [_plain(n) for n in names]


def _files(folder: Path) -> list[Path] | None:
    info = _find(folder, "info.dat")
    if info is None:
        return None
    try:
        data = _info(info.read_bytes())
    except OSError:
        return None
    out = [info]
    for n in _listed(data):
        p = _find(folder, n) if n else None
        if p is not None and not p.is_symlink():
            out.append(p)
    return out


def _info_bytes(raw: bytes) -> bytes:
    """What SongCore hashes of Info.dat: raw bytes for v2/v3, the UTF-8 text for v4."""
    if not _is_v4(_info(raw)):
        return raw
    try:
        return raw.decode("utf-8-sig").encode("utf-8")
    except UnicodeDecodeError:
        return raw


def songcore_hash(folder: Path) -> str | None:
    """The level hash of a map folder, or None without a readable Info.dat."""
    files = _files(folder)
    if files is None:
        return None
    # nosemgrep: insecure-hash-algorithm-sha1 - SongCore level id is SHA1; interop, not security
    h = hashlib.sha1(usedforsecurity=False)  # nosec B324
    try:
        h.update(_info_bytes(files[0].read_bytes()))
        for p in files[1:]:
            h.update(p.read_bytes())
    except OSError:
        return None
    return h.hexdigest().upper()


def _stamp(files: list[Path]) -> Stamp:
    out = []
    for p in files:
        st = p.stat()
        out.append((p.name, st.st_mtime_ns, st.st_size))
    return tuple(out)


class HashCache:
    """Hashes keyed by the folder's relevant file names, mtimes and sizes: a rewrite misses."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memo: dict[Path, tuple[Stamp, str | None]] = {}

    def get(self, folder: Path) -> str | None:
        try:
            files = _files(folder)
            stamp = _stamp(files) if files else None
        except OSError:
            return None
        if stamp is None:
            return None
        with self._lock:
            hit = self._memo.get(folder)
        if hit and hit[0] == stamp:
            return hit[1]
        value = songcore_hash(folder)
        with self._lock:
            self._memo[folder] = (stamp, value)
        return value
