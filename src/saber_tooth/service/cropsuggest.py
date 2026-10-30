"""Service side of Auto crop: the three best windows of a map, cached per map file mtime."""

import threading
from pathlib import Path

from saber_tooth.crop.suggest import TARGETS, suggest_crops
from saber_tooth.service.crop import _timeline

_lock = threading.Lock()
_cache: dict[tuple[str, str], tuple[tuple, dict]] = {}


def _stamp(folder: Path) -> tuple:
    """Name, mtime and size of every file: a rewritten or replaced map never matches the old one."""
    stats = ((p.name, p.stat()) for p in sorted(folder.iterdir()) if p.is_file())
    return tuple((name, st.st_mtime_ns, st.st_size) for name, st in stats)


def _body(map_id: str, tl) -> dict:
    picks = suggest_crops(
        tl.series, tl.hardest, tl.grid.bars, tl.timing.to_seconds, tl.sections.boundaries,
        tl.duration_s,
    )  # fmt: skip
    shortest = min(TARGETS) - 10
    reason = None
    if not picks:
        reason = (
            f"The song is {tl.duration_s:.0f} s long; Auto needs at least {shortest} s. "
            "Use a custom crop."
        )
    return {
        "map_id": map_id,
        "duration_s": tl.duration_s,
        "reason": reason,
        "suggestions": [
            {
                "rank": i + 1,
                "start_beat": s.start_beat,
                "end_beat": s.end_beat,
                "start_s": s.start_s,
                "end_s": s.end_s,
                "length_s": s.length_s,
                "target": f"{s.target_s // 60} min",
                "score": s.score,
                "reason": s.reason,
            }
            for i, s in enumerate(picks)
        ],
    }


def crop_suggestions(svc, map_id: str) -> dict:
    """Up to three ranked windows for the map; fast, no job, recomputed when a map file changes."""
    folder = svc._folder(map_id)
    key = (str(svc.levels), map_id)
    stamp = _stamp(folder)
    with _lock:
        hit = _cache.get(key)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    body = _body(map_id, _timeline(svc, map_id)[2])
    with _lock:
        _cache[key] = (stamp, body)
    return body
