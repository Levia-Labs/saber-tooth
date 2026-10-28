# Task 1: Errors, bar and phrase grid, shared test helpers

**Files:**

- Create: `src/saber_tooth/crop/__init__.py`
- Create: `src/saber_tooth/crop/errors.py`
- Create: `src/saber_tooth/crop/phrases.py`
- Create: `tests/crop_helpers.py`
- Test: `tests/test_crop_phrases.py`

**Interfaces:**

Consumes: `Beatmap`, `Difficulty`, `BpmEvent`, `DIFFICULTIES` (`saber_tooth/model.py`); `Timing(bpm: float, changes: list[BpmEvent])` with `to_seconds(beat)` and `to_beats(seconds)` (`saber_tooth/timing.py`); `BAR = 4.0` (`saber_tooth/lightshow/units.py`); `Analysis.beats: list[float]` (`saber_tooth/analysis.py`).

Produces (`saber_tooth.crop.errors`):

```python
class CropError(ValueError): ...


class NoNotes(CropError): ...


class InvalidWindow(CropError): ...
```

Produces (`saber_tooth.crop.phrases`):

```python
PHRASE_BARS = 8
PHRASE_BEATS = 32.0
EPS = 1e-6

@dataclass(frozen=True)
class Grid:
    anchor: float
    end_beat: float
    bars: list[float]            # property: bar-line beats anchor, anchor+4, ... <= end_beat
    phrase_starts: list[float]   # property: bars[::8]

def hardest(beatmap: Beatmap) -> Difficulty
def first_note_beat(beatmap: Beatmap) -> float | None
def grid_events(beatmap: Beatmap) -> list[BpmEvent]
def grid_timing(beatmap: Beatmap) -> Timing
def build_grid(beatmap: Beatmap, duration_s: float) -> Grid
def tempo_at(bpm: float, changes: list[BpmEvent], beat: float) -> float
def grid_drift(grid: Grid, timing: Timing, analysis: Analysis | None) -> float | None
```

Produces (`tests/crop_helpers.py`, used by later tasks): `NAME`, `DENSITY`, `info(bpm=120.0) -> MapInfo`, `diff(name, beats=(), bpm_events=()) -> Difficulty`, `beatmap(bpm=120.0, **diffs) -> Beatmap`, `stepped_map(bars=72, bpm=120.0, density=DENSITY) -> Beatmap`, `write_original(levels, name=NAME, bm=None) -> Path`.

- [ ] **Step 1: Write the failing test**

Create `tests/crop_helpers.py`:

```python
"""Synthetic maps for the crop tests. Nothing here reads or writes real user data."""

from pathlib import Path

from saber_tooth.mapio import write_map
from saber_tooth.model import (
    DIFFICULTIES,
    BasicEvent,
    Beatmap,
    BpmEvent,
    Color,
    Cut,
    Difficulty,
    MapInfo,
    Note,
)

NAME = "Song"
DENSITY = (1, 1, 3, 3, 2, 4, 4, 1, 2)  # notes per bar, one value per 8-bar section


def info(bpm: float = 120.0) -> MapInfo:
    return MapInfo(
        "Song", "", "Artist", "Mapper", bpm, "song.ogg", "cover.jpg", 10.0, 12.0,
        "DefaultEnvironment",
    )  # fmt: skip


def diff(name: str, beats=(), bpm_events: list[BpmEvent] | tuple = ()) -> Difficulty:
    d = Difficulty(name, 16.0, 0.0)
    d.notes = [Note(float(b), i % 4, 0, Color(i % 2), Cut.ANY) for i, b in enumerate(beats)]
    d.bpm_events = list(bpm_events)
    return d


def beatmap(bpm: float = 120.0, **diffs: Difficulty) -> Beatmap:
    return Beatmap(info(bpm), dict(diffs))


def stepped_map(bars: int = 72, bpm: float = 120.0, density=DENSITY) -> Beatmap:
    """All five difficulties; `density[bar // 8 % len(density)]` notes per bar, one light per bar."""
    out: dict[str, Difficulty] = {}
    for name in DIFFICULTIES:
        beats = [
            bar * 4.0 + k for bar in range(bars) for k in range(density[(bar // 8) % len(density)])
        ]
        d = diff(name, beats)
        d.events = [BasicEvent(bar * 4.0, 1, 5) for bar in range(bars)]
        out[name] = d
    return Beatmap(info(bpm), out)


def write_original(levels: Path, name: str = NAME, bm: Beatmap | None = None) -> Path:
    """Write a map folder with a 2-byte song and cover, like the repo fixtures."""
    folder = levels / name
    write_map(bm or stepped_map(), folder, None)
    (folder / "song.ogg").write_bytes(b"og")
    (folder / "cover.jpg").write_bytes(b"jp")
    return folder
```

Create `tests/test_crop_phrases.py`:

```python
import pytest

from saber_tooth.analysis import Analysis
from saber_tooth.crop.errors import NoNotes
from saber_tooth.crop.phrases import (
    build_grid,
    grid_drift,
    grid_events,
    grid_timing,
    hardest,
    tempo_at,
)
from saber_tooth.model import BpmEvent
from saber_tooth.timing import Timing
from tests.crop_helpers import beatmap, diff


def test_phrase_grid_with_bpm_change():
    bm = beatmap(Expert=diff("Expert", [5.5, 9.0], bpm_events=[BpmEvent(40.0, 60.0)]))
    grid = build_grid(bm, 60.0)
    assert grid.anchor == 4.0
    assert grid.end_beat == pytest.approx(80.0)  # 20 s at 120 bpm, then 40 s at 60 bpm
    assert grid.bars[0] == 4.0 and grid.bars[-1] == 80.0 and len(grid.bars) == 20
    assert grid.phrase_starts == [4.0, 36.0, 68.0]


def test_anchor_skips_a_note_free_intro():
    bm = beatmap(Expert=diff("Expert", [21.0]))
    assert build_grid(bm, 100.0).anchor == 20.0


def test_anchor_is_zero_when_notes_start_at_once():
    assert build_grid(beatmap(Expert=diff("Expert", [0.0, 1.0])), 30.0).anchor == 0.0


def test_grid_events_come_from_the_hardest_difficulty_with_notes():
    bm = beatmap(
        Easy=diff("Easy", [1.0], bpm_events=[BpmEvent(8.0, 90.0)]),
        Expert=diff("Expert", [1.0], bpm_events=[BpmEvent(8.0, 100.0)]),
        ExpertPlus=diff("ExpertPlus", []),
    )
    assert grid_events(bm) == [BpmEvent(8.0, 100.0)]
    assert hardest(bm).name == "Expert"


def test_a_map_without_notes_raises_no_notes():
    with pytest.raises(NoNotes):
        build_grid(beatmap(Expert=diff("Expert", [])), 30.0)
    with pytest.raises(NoNotes):
        build_grid(beatmap(), 30.0)


def test_tempo_at_follows_timing_rules():
    changes = [BpmEvent(40.0, 60.0), BpmEvent(0.0, 90.0)]
    assert tempo_at(120.0, changes, 0.0) == 90.0  # a change at beat 0 overrides the base
    assert tempo_at(120.0, changes, 39.99) == 90.0
    assert tempo_at(120.0, changes, 40.0) == 60.0
    assert tempo_at(120.0, [], 500.0) == 120.0


def test_tempo_at_matches_the_timing_slope():
    changes = [BpmEvent(8.0, 60.0), BpmEvent(24.0, 180.0)]
    timing = Timing(120.0, changes)
    for beat in (0.0, 7.0, 8.0, 20.0, 24.0, 30.0):
        bpm = tempo_at(120.0, changes, beat)
        assert timing.to_seconds(beat + 1) - timing.to_seconds(beat) == pytest.approx(60.0 / bpm)


def _analysis(beats: list[float]) -> Analysis:
    return Analysis("x", "C", 120.0, beats, [], [], [], None)


def test_grid_drift_is_the_median_distance_to_the_nearest_analyser_beat():
    bm = beatmap(Expert=diff("Expert", [0.0]))
    grid = build_grid(bm, 20.0)  # a bar line every 2 s
    timing = grid_timing(bm)
    aligned = _analysis([i * 0.5 for i in range(41)])
    shifted = _analysis([i * 0.5 + 0.2 for i in range(41)])
    assert grid_drift(grid, timing, aligned) == pytest.approx(0.0)
    assert grid_drift(grid, timing, shifted) == pytest.approx(0.2)
    assert grid_drift(grid, timing, None) is None
    assert grid_drift(grid, timing, _analysis([])) is None
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_crop_phrases.py -q`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'saber_tooth.crop'`.

Continued in [task-01b.md](task-01b.md).
