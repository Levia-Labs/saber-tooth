# Task 9: Timeline assembly and window resolution (part b)

Continues [task-09a.md](task-09a.md).

- [ ] **Step 3: Implement**

Create `src/saber_tooth/crop/timeline.py`:

```python
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


def resolve_window(
    tl: Timeline, start_beat: float, end_beat: float
) -> tuple[CropPlan, StartPoint, EndPoint]:
    """The plan, start and end a requested pair names, or InvalidWindow naming the broken rule."""
    if end_beat <= start_beat:
        raise InvalidWindow("end_beat must be after start_beat")
    enabled = [p for p in tl.plans.values() if p.enabled]
    if not enabled:
        raise InvalidWindow("no crop length is available for this song")
    holders = [(p, s) for p in enabled for s in p.starts if _same(s.beat, start_beat)]
    if not holders:
        raise InvalidWindow("start_beat is not a section boundary with a window in the band")
    length = tl.timing.to_seconds(end_beat) - tl.timing.to_seconds(start_beat)
    in_band = [(p, s) for p, s in holders if p.band[0] - EPS <= length <= p.band[1] + EPS]
    if not in_band:
        bands = " and ".join(f"{p.band[0]:g}-{p.band[1]:g} s" for p in enabled)
        raise InvalidWindow(f"the length {length:.1f} s is outside the bands {bands}")
    for plan, start in in_band:
        for end in start.ends:
            if _same(end.beat, end_beat):
                return plan, start, end
    raise InvalidWindow("end_beat is not an allowed end point for that start")


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
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_crop_timeline.py -q`
Expected: 9 passed (the parametrized rule test counts four).

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/crop/timeline.py tests/test_crop_timeline.py && uv run ruff format --check src/saber_tooth/crop/timeline.py tests/test_crop_timeline.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: crop timeline assembly and window resolution"` (subagents never commit).

---
