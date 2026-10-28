# Task 4: Section detection

**Files:**

- Create: `src/saber_tooth/crop/sections.py`
- Test: `tests/test_crop_sections.py`

**Interfaces:**

Consumes: `Grid`, `PHRASE_BEATS`, `EPS`, `hardest` (`crop/phrases.py`); `note_beats`, `mean_nps`, `peak` (`crop/nps.py`); `Analysis`, `onset_density(a, start_s, end_s)` (`analysis.py`); `BOX_KEYS` (`mapio/write.py`).

Produces (`saber_tooth.crop.sections`):

```python
PERCENTILE = 0.70
MIN_SECTION_BEATS = 32.0

@dataclass(frozen=True)
class Section:
    start_beat: float
    end_beat: float
    nps: float          # mean NPS of the hardest difficulty
    intensity: float    # nps / song peak, 0..1

@dataclass(frozen=True)
class SectionMap:
    boundaries: list[float]   # beats, ascending; first is the grid anchor
    sections: list[Section]   # between consecutive boundaries
    map_only: bool

def light_count(d: Difficulty, lo: float, hi: float) -> int
def make_features(beatmap: Beatmap, timing: Timing, analysis: Analysis | None) -> Callable[[float, float], list[float]]
def change_scores(grid: Grid, features: Callable[[float, float], list[float]]) -> list[tuple[float, float]]
def pick_boundaries(grid: Grid, scored: list[tuple[float, float]]) -> list[float]
def find_sections(beatmap: Beatmap, grid: Grid, timing: Timing, analysis: Analysis | None, series: list[float]) -> SectionMap
```

`features(lo, hi)` takes a beat window and returns one rate per term; map terms first (lights per bar, notes per bar), then, when analysed, drums, bass and chords per second, melody notes per second, melody pitch range.

- [ ] **Step 1: Write the failing test**

Create `tests/test_crop_sections.py`:

```python
import math

from saber_tooth.analysis import Analysis
from saber_tooth.crop.nps import nps_series
from saber_tooth.crop.phrases import Grid, build_grid, grid_timing, hardest
from saber_tooth.crop.sections import change_scores, find_sections, pick_boundaries
from tests.crop_helpers import stepped_map

DURATION = 80.0  # stepped_map(40) at 120 bpm: last note at beat 157, song end at beat 160


def test_change_scores_find_clear_energy_steps():
    grid = Grid(0.0, 192.0)

    def features(lo: float, hi: float) -> list[float]:
        return [1.0 if 64.0 <= lo < 128.0 else 0.0]  # a loud chorus from beat 64 to 128

    scored = change_scores(grid, features)
    assert scored == [(32.0, 0.0), (64.0, 1.0), (96.0, 0.0), (128.0, 1.0), (160.0, 0.0)]
    assert pick_boundaries(grid, scored) == [0.0, 64.0, 128.0, 192.0]


def test_a_boundary_closer_than_eight_bars_keeps_the_higher_score():
    grid = Grid(0.0, 192.0)
    scored = [(32.0, 0.9), (48.0, 0.95), (96.0, 0.1), (128.0, 0.1), (160.0, 0.1)]
    assert pick_boundaries(grid, scored) == [0.0, 48.0, 192.0]


def test_the_song_end_beats_a_boundary_closer_than_eight_bars():
    grid = Grid(0.0, 144.0)
    scored = [(32.0, 0.5), (64.0, 0.9), (96.0, 0.1), (128.0, 0.95)]
    assert pick_boundaries(grid, scored) == [0.0, 144.0]


def test_a_flat_or_tiny_song_has_no_inner_boundary():
    assert pick_boundaries(Grid(0.0, 192.0), [(32.0, 0.0), (64.0, 0.0)]) == [0.0, 192.0]
    assert pick_boundaries(Grid(0.0, 6.0), []) == [0.0]


def _sections(bm, analysis):
    grid = build_grid(bm, DURATION)
    timing = grid_timing(bm)
    series = nps_series(hardest(bm), timing, DURATION)
    return find_sections(bm, grid, timing, analysis, series)


def test_without_analysis_sections_are_map_only():
    bm = stepped_map(bars=40, density=(1, 1, 3, 3, 2))
    result = _sections(bm, None)
    assert result.map_only is True
    # candidates are beats 32, 64, 96, 128 with scores 0, 1, 0, 0.5; only 1 is above the 70th
    # percentile (0.55); the last bar line of an 80 s song at 120 bpm is beat 160
    assert result.boundaries == [0.0, 64.0, 160.0]
    assert [s.start_beat for s in result.sections] == [0.0, 64.0]
    assert all(0.0 <= s.intensity <= 1.0 for s in result.sections)
    assert result.sections[1].nps > result.sections[0].nps


def test_audio_terms_find_a_step_the_map_does_not_show():
    bm = stepped_map(bars=40, density=(2,))  # flat map: no step in notes or lights
    kick = [32.0 + i * 0.25 for i in range(190)]  # drums enter at 32 s = beat 64
    analysis = Analysis("x", "C", 120.0, [], kick, [], [], None)
    assert _sections(bm, None).boundaries == [0.0, 160.0]
    with_audio = _sections(bm, analysis)
    assert with_audio.map_only is False
    assert with_audio.boundaries == [0.0, 64.0, 160.0]


def test_pitched_terms_count_when_present():
    bm = stepped_map(bars=40, density=(2,))
    melody = [32.0 + i * 0.5 for i in range(90)]
    ids = [50 + (i % 7) for i in range(90)]
    analysis = Analysis("x", "C", 120.0, [], [], [], [], None, [], [], melody, ids)
    result = _sections(bm, analysis)
    assert result.boundaries == [0.0, 64.0, 160.0]
    assert math.isclose(sum(s.end_beat - s.start_beat for s in result.sections), 160.0)
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_crop_sections.py -q`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'saber_tooth.crop.sections'`.

- [ ] **Step 3: Implement**

Create `src/saber_tooth/crop/sections.py`:

```python
"""Song sections: where the music changes, found from the map and, when analysed, the audio."""

import math
from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass

from saber_tooth.analysis import Analysis, onset_density
from saber_tooth.crop.nps import mean_nps, note_beats, peak
from saber_tooth.crop.phrases import EPS, PHRASE_BEATS, Grid, hardest
from saber_tooth.lightshow.units import BAR
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import Beatmap, Difficulty
from saber_tooth.timing import Timing

PERCENTILE = 0.70
MIN_SECTION_BEATS = PHRASE_BEATS  # a section is at least 8 bars


@dataclass(frozen=True)
class Section:
    start_beat: float
    end_beat: float
    nps: float
    intensity: float


@dataclass(frozen=True)
class SectionMap:
    boundaries: list[float]
    sections: list[Section]
    map_only: bool


def _count(times: list[float], lo: float, hi: float) -> int:
    return bisect_left(times, hi) - bisect_left(times, lo)


def _in(beat: object, lo: float, hi: float) -> bool:
    return isinstance(beat, int | float) and not isinstance(beat, bool) and lo <= beat < hi


def light_count(d: Difficulty, lo: float, hi: float) -> int:
    """Basic events, boost events and event box groups that start in [lo, hi)."""
    n = sum(1 for e in d.events if lo <= e.beat < hi) + sum(1 for b, _ in d.boosts if lo <= b < hi)
    for key in BOX_KEYS:
        n += sum(1 for g in d.raw.get(key, []) if isinstance(g, dict) and _in(g.get("b"), lo, hi))
    return n


def _pitch_range(a: Analysis, lo_s: float, hi_s: float) -> float:
    ids = a.melody_ids[bisect_left(a.melody, lo_s) : bisect_left(a.melody, hi_s)]
    return float(max(ids) - min(ids)) if len(ids) > 1 else 0.0


def make_features(
    beatmap: Beatmap, timing: Timing, analysis: Analysis | None
) -> Callable[[float, float], list[float]]:
    diffs = list(beatmap.difficulties.values())
    heads = note_beats(hardest(beatmap))

    def features(lo: float, hi: float) -> list[float]:
        bars = (hi - lo) / BAR
        out = [max(light_count(d, lo, hi) for d in diffs) / bars, _count(heads, lo, hi) / bars]
        if analysis is not None:
            a, b = timing.to_seconds(lo), timing.to_seconds(hi)
            secs = b - a
            out += [
                onset_density(analysis, a, b),
                (_count(analysis.bass, a, b) + _count(analysis.chords, a, b)) / secs,
                _count(analysis.melody, a, b) / secs,
                _pitch_range(analysis, a, b),
            ]
        return out

    return features


def change_scores(
    grid: Grid, features: Callable[[float, float], list[float]]
) -> list[tuple[float, float]]:
    """(beat, score) per phrase start with a full phrase on each side: the sum over terms of the
    jump between the 8 bars before and the 8 bars after, each term divided by its song maximum."""
    jumps: list[tuple[float, list[float]]] = []
    beat = grid.anchor + PHRASE_BEATS
    while beat + PHRASE_BEATS <= grid.end_beat + EPS:
        before = features(beat - PHRASE_BEATS, beat)
        after = features(beat, beat + PHRASE_BEATS)
        jumps.append((beat, [abs(x - y) for x, y in zip(after, before, strict=True)]))
        beat += PHRASE_BEATS
    if not jumps:
        return []
    peaks = [max(j[i] for _, j in jumps) for i in range(len(jumps[0][1]))]
    return [
        (b, sum(v / p if p > 0 else 0.0 for v, p in zip(j, peaks, strict=True))) for b, j in jumps
    ]


def _percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def pick_boundaries(grid: Grid, scored: list[tuple[float, float]]) -> list[float]:
    """The grid anchor, every score above the 70th percentile, and the last bar line. Boundaries
    closer than 8 bars keep the higher score; the anchor and the last bar line always win."""
    bars = grid.bars
    if len(bars) < 2:
        return bars[:1]
    threshold = _percentile([s for _, s in scored], PERCENTILE) if scored else 0.0
    picks = [(grid.anchor, math.inf)]
    picks += [(b, s) for b, s in scored if s > threshold]
    picks.append((bars[-1], math.inf))
    kept: list[tuple[float, float]] = []
    for beat, score in picks:
        if kept and beat - kept[-1][0] < MIN_SECTION_BEATS - EPS:
            if score > kept[-1][1]:
                kept[-1] = (beat, score)
            continue
        kept.append((beat, score))
    return [b for b, _ in kept]


def find_sections(
    beatmap: Beatmap,
    grid: Grid,
    timing: Timing,
    analysis: Analysis | None,
    series: list[float],
) -> SectionMap:
    """Sections between boundaries, each with its mean NPS and intensity against the song peak."""
    scored = change_scores(grid, make_features(beatmap, timing, analysis))
    bounds = pick_boundaries(grid, scored)
    top = peak(series)
    sections = []
    for a, b in zip(bounds, bounds[1:], strict=False):
        nps = mean_nps(series, timing.to_seconds(a), timing.to_seconds(b))
        sections.append(Section(a, b, nps, nps / top if top > 0 else 0.0))
    return SectionMap(bounds, sections, analysis is None)
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_crop_sections.py -q`
Expected: 7 passed.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/crop/sections.py tests/test_crop_sections.py && uv run ruff format --check src/saber_tooth/crop/sections.py tests/test_crop_sections.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: crop section detection"` (subagents never commit).
