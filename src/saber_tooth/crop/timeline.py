"""Everything the crop panel and the crop job need, built in one call."""

from dataclasses import dataclass

from saber_tooth.analysis import Analysis
from saber_tooth.crop.errors import InvalidWindow
from saber_tooth.crop.nps import all_series
from saber_tooth.crop.phrases import EPS, Grid, build_grid, grid_drift, grid_timing, hardest
from saber_tooth.crop.sections import SectionMap, find_sections
from saber_tooth.crop.window import (
    TARGETS,
    CropPlan,
    EndPoint,
    StartPoint,
    Window,
    build_plan,
)
from saber_tooth.model import Beatmap
from saber_tooth.timing import Timing


@dataclass(frozen=True)
class Timeline:
    beatmap: Beatmap
    duration_s: float
    grid: Grid
    timing: Timing
    hardest: str
    series: dict[str, list[float]]
    sections: SectionMap
    plans: dict[int, CropPlan]
    drift_s: float | None


def build_timeline(beatmap: Beatmap, duration_s: float, analysis: Analysis | None) -> Timeline:
    hard = hardest(beatmap)  # NoNotes when no Standard difficulty has a note
    timing = grid_timing(beatmap)
    grid = build_grid(beatmap, duration_s)
    series = all_series(beatmap, timing, duration_s)
    sections = find_sections(beatmap, grid, timing, analysis, series[hard.name])
    plans = {
        target: build_plan(grid, sections, series[hard.name], timing, target, duration_s)
        for target in TARGETS
    }
    return Timeline(
        beatmap, duration_s, grid, timing, hard.name, series, sections, plans,
        grid_drift(grid, timing, analysis),
    )  # fmt: skip


def _same(a: float, b: float) -> bool:
    return abs(a - b) < EPS


MIN_LENGTH_S = 1.0


@dataclass(frozen=True)
class Resolved:
    start_beat: float
    end_beat: float
    start_s: float
    end_s: float

    @property
    def length_s(self) -> float:
        return self.end_s - self.start_s


def resolve_window(tl: Timeline, start_beat: float, end_beat: float) -> Resolved:
    """The free window a request names, or InvalidWindow naming the broken rule. Any start and
    end inside the song is allowed as long as the window is at least MIN_LENGTH_S long."""
    if end_beat <= start_beat:
        raise InvalidWindow("end_beat must be after start_beat")
    start_s, end_s = tl.timing.to_seconds(start_beat), tl.timing.to_seconds(end_beat)
    if start_beat < 0 or end_s > tl.duration_s + EPS:
        raise InvalidWindow("the window must lie inside the song")
    if end_s - start_s < MIN_LENGTH_S - EPS:
        raise InvalidWindow("the window must be at least 1 second long")
    return Resolved(start_beat, end_beat, start_s, end_s)


def window_label(tl: Timeline, length_s: float) -> str:
    """Return "1 min" or "2 min" within that plan's band, else "crop MmSSs" (rounded seconds)."""
    for target, plan in tl.plans.items():
        if plan.band[0] - EPS <= length_s <= plan.band[1] + EPS:
            return f"{target // 60} min"
    total = round(length_s)
    return f"crop {total // 60}m{total % 60:02d}s"


def _end(e: EndPoint) -> dict:
    return {"beat": e.beat, "seconds": e.seconds, "kind": e.kind}


def _start(s: StartPoint) -> dict:
    return {"beat": s.beat, "seconds": s.seconds, "ends": [_end(e) for e in s.ends]}


def _window(w: Window) -> dict:
    return {
        "start_beat": w.start_beat,
        "end_beat": w.end_beat,
        "start_s": w.start_s,
        "end_s": w.end_s,
        "length_s": w.length_s,
        "end_kind": w.end_kind,
        "score": w.score,
    }


def _plan(p: CropPlan) -> dict:
    return {
        "enabled": p.enabled,
        "reason": p.reason,
        "band": list(p.band),
        "suggestions": [_window(w) for w in p.suggestions],
        "starts": [_start(s) for s in p.starts],
    }


def timeline_dict(tl: Timeline, map_id: str) -> dict:
    """The JSON body of `GET /api/maps/{id}/timeline`; times in beats and seconds."""
    return {
        "map_id": map_id,
        "min_length_s": MIN_LENGTH_S,
        "duration_s": tl.duration_s,
        "bpm": tl.beatmap.info.bpm,
        "hardest": tl.hardest,
        "map_only": tl.sections.map_only,
        "grid_drift_s": tl.drift_s,
        "nps": tl.series,
        "sections": [
            {
                "start_beat": s.start_beat,
                "end_beat": s.end_beat,
                "start_s": tl.timing.to_seconds(s.start_beat),
                "end_s": tl.timing.to_seconds(s.end_beat),
                "nps": s.nps,
                "intensity": s.intensity,
            }
            for s in tl.sections.sections
        ],
        "lengths": {str(target): _plan(plan) for target, plan in tl.plans.items()},
    }
