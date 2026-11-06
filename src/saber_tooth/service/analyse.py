"""The analyser's result for a map's audio, cached per unchanged audio file."""

import logging
from pathlib import Path

from saber_tooth.analyser_client import AnalyserError, AnalyserTimeout
from saber_tooth.analysis import Analysis
from saber_tooth.mapio import MapParseError
from saber_tooth.mapio.errors import safe_name
from saber_tooth.model import Beatmap
from saber_tooth.service.errors import AnalysisUnavailable

log = logging.getLogger(__name__)
ANALYSIS_CACHE = 16  # analyser results kept so Scan and Fix do not analyse one song twice


def analyse_map(svc, map_id: str, bm: Beatmap, folder: Path, progress=None) -> Analysis | None:
    """One analyser call per audio file while it is unchanged.

    None when the map has no usable audio file. With audio, an analyser that gives nothing
    after the client's retries raises AnalysisUnavailable (Fix fails and can be run again;
    scan flags its result); one slower than the stage timeout raises AnalyserTimeout."""
    try:
        audio = folder / safe_name(bm.info.song_file)
        if not audio.is_file():
            return None
        stat = audio.stat()
    except (MapParseError, OSError):
        return None
    key = (str(audio.resolve()), stat.st_size, stat.st_mtime_ns)
    with svc._analysis_lock:
        hit = svc._analyses.get(key)
    if hit is not None and (hit.audio is None or hit.audio.exists()):
        return hit
    try:
        found = svc.client.analyse_file(audio, f"{map_id}.ogg", getattr(progress, "check", None))
    except AnalyserTimeout:
        raise
    except (AnalyserError, ValueError, MapParseError, OSError, KeyError) as exc:
        log.warning("analysis of %s failed: %r", map_id, exc)
        if getattr(svc, "analysis_optional", False):  # the offline autofix tool has no analyser
            return None
        raise AnalysisUnavailable(exc) from exc
    with svc._analysis_lock:
        svc._analyses[key] = found
        while len(svc._analyses) > ANALYSIS_CACHE:
            svc._analyses.pop(next(iter(svc._analyses)))
    return found
