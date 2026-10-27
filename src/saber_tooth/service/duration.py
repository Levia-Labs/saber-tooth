"""Song length of a map: Ogg granule position, Info songDuration, else the last object's time."""

import logging
import math
import struct
from pathlib import Path

from saber_tooth.model import Beatmap
from saber_tooth.timing import Timing

log = logging.getLogger(__name__)

WINDOW = 64 * 1024
AUDIO_SUFFIXES = {".egg", ".ogg"}
_ID_HEADER = b"\x01vorbis"
_PAGE = b"OggS"


def _vorbis_rate(head: bytes) -> int | None:
    at = head.find(_ID_HEADER)
    if at < 0:
        return None
    # tag(7) version(4) channels(1) sample_rate(4)
    fields = head[at + 7 : at + 16]
    if len(fields) < 9:
        return None
    rate = struct.unpack("<I", fields[5:9])[0]
    return rate or None


def _last_granule(tail: bytes) -> int | None:
    end = len(tail)
    while True:
        at = tail.rfind(_PAGE, 0, end)
        if at < 0:
            return None
        if len(tail) - at >= 14:
            granule = struct.unpack("<q", tail[at + 6 : at + 14])[0]
            if granule >= 0:
                return granule
        end = at


def ogg_duration(path: Path) -> float | None:
    """Seconds of a Vorbis Ogg file from its first and last 64 KB; None if not recognisable."""
    try:
        with path.open("rb") as fh:
            head = fh.read(WINDOW)
            size = fh.seek(0, 2)
            fh.seek(max(0, size - WINDOW))
            tail = fh.read(WINDOW)
    except OSError:
        return None
    rate = _vorbis_rate(head) if head.startswith(_PAGE) else None
    granule = _last_granule(tail)
    if not rate or not granule:
        return None
    return granule / rate


def audio_path(folder: Path, name: str) -> Path | None:
    """The song file inside folder, or None; never a path outside it."""
    if not name or Path(name).name != name or Path(name).suffix.lower() not in AUDIO_SUFFIXES:
        return None
    if any(c in name for c in "/\\:\x00"):
        return None
    try:
        root = folder.resolve()
        found = next((p for p in folder.iterdir() if p.name.lower() == name.lower()), None)
        if found is None or found.is_symlink() or found.resolve().parent != root:
            return None
        return found if found.is_file() else None
    except OSError:
        return None


def _valid(seconds: object) -> float | None:
    ok = isinstance(seconds, int | float) and math.isfinite(seconds) and seconds > 0
    return float(seconds) if ok else None  # type: ignore[arg-type]


def _from_notes(beatmap: Beatmap) -> float | None:
    best: float | None = None
    for diff in beatmap.difficulties.values():
        beats = [o.beat for o in (*diff.notes, *diff.bombs)]
        beats += [w.beat + max(w.duration, 0.0) for w in diff.walls]
        if not beats:
            continue
        try:
            secs = Timing(beatmap.info.bpm, diff.bpm_events).to_seconds(max(beats))
        except ValueError:
            continue
        best = secs if best is None else max(best, secs)
    return _valid(best)


def map_duration(folder: Path, beatmap: Beatmap, raw_info: dict | None = None) -> float | None:
    """Duration in seconds, or None; never raises."""
    try:
        song = audio_path(folder, beatmap.info.song_file)
        found = ogg_duration(song) if song else None
        if found:
            return found
        audio = (raw_info or {}).get("audio")
        if isinstance(audio, dict) and (stated := _valid(audio.get("songDuration"))):
            return stated
        return _from_notes(beatmap)
    except Exception:  # a bad file must never fail a library refresh
        log.warning("could not measure %s", folder.name, exc_info=True)
        return None
