# Task 1: Errors, bar and phrase grid, shared test helpers (part b)

Continues [task-01a.md](task-01a.md).

- [ ] **Step 3: Implement**

Create `src/saber_tooth/crop/__init__.py`:

```python
"""Crop a map to a 1 or 2 minute highlight on song-part boundaries."""
```

Create `src/saber_tooth/crop/errors.py`:

```python
"""Errors of the crop feature; the API turns a CropError into HTTP 422."""


class CropError(ValueError):
    """A crop cannot be planned or written; the message names the reason."""


class NoNotes(CropError):
    """No Standard difficulty has a note."""


class InvalidWindow(CropError):
    """The requested start and end break a window rule."""
```

Create `src/saber_tooth/crop/phrases.py`:

```python
"""Bar and phrase grid of a map, built from its tempo grid."""

import math
import statistics
from bisect import bisect_left
from dataclasses import dataclass

from saber_tooth.analysis import Analysis
from saber_tooth.crop.errors import NoNotes
from saber_tooth.lightshow.units import BAR
from saber_tooth.model import DIFFICULTIES, Beatmap, BpmEvent, Difficulty
from saber_tooth.timing import Timing

PHRASE_BARS = 8
PHRASE_BEATS = PHRASE_BARS * BAR
EPS = 1e-6


@dataclass(frozen=True)
class Grid:
    """Bar lines every 4 beats from `anchor` (a beat) up to `end_beat`."""

    anchor: float
    end_beat: float

    @property
    def bars(self) -> list[float]:
        count = int((self.end_beat - self.anchor + EPS) // BAR) + 1
        return [self.anchor + i * BAR for i in range(max(count, 0))]

    @property
    def phrase_starts(self) -> list[float]:
        return self.bars[::PHRASE_BARS]


def hardest(beatmap: Beatmap) -> Difficulty:
    """The hardest Standard difficulty that has notes."""
    for name in reversed(DIFFICULTIES):
        d = beatmap.difficulties.get(name)
        if d is not None and d.notes:
            return d
    raise NoNotes("no Standard difficulty has notes")


def first_note_beat(beatmap: Beatmap) -> float | None:
    beats = [n.beat for d in beatmap.difficulties.values() for n in d.notes]
    return min(beats, default=None)


def grid_events(beatmap: Beatmap) -> list[BpmEvent]:
    """Tempo changes of the hardest difficulty with notes: the grid every difficulty shares."""
    return list(hardest(beatmap).bpm_events)


def grid_timing(beatmap: Beatmap) -> Timing:
    return Timing(beatmap.info.bpm, grid_events(beatmap))


def build_grid(beatmap: Beatmap, duration_s: float) -> Grid:
    """Bar lines from the bar that holds the first note (any difficulty) to the song end."""
    first = first_note_beat(beatmap)
    if first is None:
        raise NoNotes("no Standard difficulty has notes")
    anchor = math.floor(first / BAR) * BAR
    return Grid(anchor, grid_timing(beatmap).to_beats(duration_s))


def tempo_at(bpm: float, changes: list[BpmEvent], beat: float) -> float:
    """Tempo in force at `beat`, by the rules of Timing (the later change wins at one beat)."""
    current = bpm
    for change in sorted((c for c in changes if 0 <= c.beat <= beat), key=lambda c: c.beat):
        current = change.bpm
    return current


def grid_drift(grid: Grid, timing: Timing, analysis: Analysis | None) -> float | None:
    """Median seconds between a map bar line and the nearest analyser beat; None unanalysed."""
    if analysis is None or not analysis.beats:
        return None
    beats = analysis.beats
    gaps = []
    for bar in grid.bars:
        t = timing.to_seconds(bar)
        i = bisect_left(beats, t)
        gaps.append(min(abs(t - beats[j]) for j in (i - 1, i) if 0 <= j < len(beats)))
    return statistics.median(gaps) if gaps else None
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_crop_phrases.py -q`
Expected: 8 passed.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/crop tests/crop_helpers.py tests/test_crop_phrases.py && uv run ruff format --check src/saber_tooth/crop tests/crop_helpers.py tests/test_crop_phrases.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: crop bar and phrase grid"` (subagents never commit).

---
