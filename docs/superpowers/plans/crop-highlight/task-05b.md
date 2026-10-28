# Task 5: Window search and snap points (part b)

Continues [task-05a.md](task-05a.md).

- [ ] **Step 3: Implement**

Create `src/saber_tooth/crop/window.py`:

```python
"""The crop window: the suggested stretch and every start and end the user may pick."""

from dataclasses import dataclass

from saber_tooth.crop.nps import mean_nps, peak, slope
from saber_tooth.crop.phrases import EPS, PHRASE_BARS, Grid
from saber_tooth.crop.sections import SectionMap
from saber_tooth.lightshow.units import BAR
from saber_tooth.timing import Timing

TARGETS = (60, 120)
BAND_PCT = 10
WEIGHT_NPS = 0.7
WEIGHT_BUILD = 0.3
PENALTY = 0.1
KINDS = ("section", "phrase", "bar4", "bar")
SUGGESTIONS = 3  # the best window and the next two


@dataclass(frozen=True)
class EndPoint:
    beat: float
    seconds: float
    kind: str


@dataclass(frozen=True)
class StartPoint:
    beat: float
    seconds: float
    ends: list[EndPoint]


@dataclass(frozen=True)
class Window:
    start_beat: float
    end_beat: float
    start_s: float
    end_s: float
    end_kind: str
    score: float

    @property
    def length_s(self) -> float:
        return self.end_s - self.start_s


@dataclass(frozen=True)
class CropPlan:
    target_s: int
    enabled: bool
    reason: str | None
    band: tuple[float, float]
    suggestions: list[Window]
    starts: list[StartPoint]


def band(target_s: int) -> tuple[float, float]:
    return target_s * (100 - BAND_PCT) / 100, target_s * (100 + BAND_PCT) / 100


def end_kind(grid: Grid, boundaries: frozenset[float], beat: float) -> str:
    if round(beat, 6) in boundaries:
        return "section"
    index = round((beat - grid.anchor) / BAR)
    if index % PHRASE_BARS == 0:
        return "phrase"
    if index % 4 == 0:
        return "bar4"
    return "bar"


def ends_for(
    grid: Grid,
    boundaries: frozenset[float],
    timing: Timing,
    start_beat: float,
    lo: float,
    hi: float,
) -> list[EndPoint]:
    """Every bar line after `start_beat` whose length from it lies in [lo, hi] seconds."""
    start_s = timing.to_seconds(start_beat)
    out: list[EndPoint] = []
    for bar in grid.bars:
        if bar <= start_beat + EPS:
            continue
        seconds = timing.to_seconds(bar)
        length = seconds - start_s
        if length > hi + EPS:
            break
        if length >= lo - EPS:
            out.append(EndPoint(bar, seconds, end_kind(grid, boundaries, bar)))
    return out


def best_end(ends: list[EndPoint], start_s: float, target_s: int) -> EndPoint:
    """The strongest kind first, then the length closest to the target, then the earlier end."""
    return min(
        ends,
        key=lambda e: (KINDS.index(e.kind), abs(e.seconds - start_s - target_s), e.beat),
    )


def window_score(mean: float, top: float, bonus: float, kind: str) -> float:
    base = WEIGHT_NPS * (mean / top if top > 0 else 0.0) + WEIGHT_BUILD * bonus
    return base - (PENALTY if kind != "section" else 0.0)


def build_up(
    sections: SectionMap, start_beat: float, series: list[float], timing: Timing, top: float
) -> float:
    """Bonus in [0, 1]: the section starting here is quieter than the next and trends upward."""
    for i, first in enumerate(sections.sections[:-1]):
        if abs(first.start_beat - start_beat) > EPS:
            continue
        nxt = sections.sections[i + 1]
        a, b = timing.to_seconds(first.start_beat), timing.to_seconds(first.end_beat)
        if top > 0 and first.nps < nxt.nps and slope(series, a, b) > 0:
            return min(1.0, (nxt.nps - first.nps) / top)
        return 0.0
    return 0.0


def _disabled(target_s: int, reason: str, lo: float, hi: float) -> CropPlan:
    return CropPlan(target_s, False, reason, (lo, hi), [], [])


def build_plan(
    grid: Grid,
    sections: SectionMap,
    series: list[float],
    timing: Timing,
    target_s: int,
    duration_s: float,
) -> CropPlan:
    lo, hi = band(target_s)
    minutes = target_s // 60
    if duration_s < hi:
        return _disabled(
            target_s,
            f"The song is {duration_s:.0f} s long; a {minutes} min crop needs at least {hi:.0f} s.",
            lo,
            hi,
        )
    boundaries = frozenset(round(b, 6) for b in sections.boundaries)
    top = peak(series)
    starts: list[StartPoint] = []
    windows: list[Window] = []
    for beat in sections.boundaries:
        ends = ends_for(grid, boundaries, timing, beat, lo, hi)
        if not ends:
            continue
        start_s = timing.to_seconds(beat)
        starts.append(StartPoint(beat, start_s, ends))
        end = best_end(ends, start_s, target_s)
        mean = mean_nps(series, start_s, end.seconds)
        bonus = build_up(sections, beat, series, timing, top)
        score = window_score(mean, top, bonus, end.kind)
        windows.append(Window(beat, end.beat, start_s, end.seconds, end.kind, score))
    if not starts:
        return _disabled(
            target_s,
            f"No section boundary leaves room for a {minutes} min window "
            f"between {lo:.0f} s and {hi:.0f} s.",
            lo,
            hi,
        )
    windows.sort(key=lambda w: (-w.score, w.start_beat))
    return CropPlan(target_s, True, None, (lo, hi), windows[:SUGGESTIONS], starts)
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_crop_window.py -q`
Expected: 11 passed.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/crop/window.py tests/test_crop_window.py && uv run ruff format --check src/saber_tooth/crop/window.py tests/test_crop_window.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: crop window search and snap points"` (subagents never commit).

---
