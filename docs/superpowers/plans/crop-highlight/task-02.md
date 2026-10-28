# Task 2: NPS series

**Files:**

- Create: `src/saber_tooth/crop/nps.py`
- Test: `tests/test_crop_nps.py`

**Interfaces:**

Consumes: `Difficulty`, `Beatmap`, `DIFFICULTIES`; `Timing`.

Produces (`saber_tooth.crop.nps`):

```python
def note_beats(d: Difficulty) -> list[float]            # ascending; arcs add none, chain adds its head once
def nps_series(d: Difficulty, timing: Timing, duration_s: float) -> list[float]   # len = max(1, ceil(duration_s))
def all_series(beatmap: Beatmap, timing: Timing, duration_s: float) -> dict[str, list[float]]  # difficulties with notes
def peak(series: list[float]) -> float
def mean_nps(series: list[float], start_s: float, end_s: float) -> float
def slope(series: list[float], start_s: float, end_s: float) -> float
```

- [ ] **Step 1: Write the failing test**

Create `tests/test_crop_nps.py`:

```python
import pytest

from saber_tooth.crop.nps import all_series, mean_nps, note_beats, nps_series, peak, slope
from saber_tooth.model import Bomb
from saber_tooth.timing import Timing
from tests.crop_helpers import beatmap, diff


def _chain_diff():
    d = diff("Expert", [0.0, 1.0])  # notes (0.0, x0, y0, red) and (1.0, x1, y0, blue)
    d.bombs = [Bomb(0.0, 0, 0), Bomb(1.5, 1, 1)]
    d.raw = {
        "sliders": [{"b": 0.0, "tb": 1.0, "x": 0, "y": 0, "c": 0, "tx": 1, "ty": 0}],
        "burstSliders": [
            {"b": 1.0, "tb": 3.0, "x": 1, "y": 0, "c": 1, "tx": 2, "ty": 1, "sc": 4},
            {"b": 2.0, "tb": 4.0, "x": 3, "y": 1, "c": 0, "tx": 2, "ty": 1, "sc": 4},
        ],
    }
    return d


def test_bombs_and_arcs_are_excluded_and_a_chain_counts_once():
    assert note_beats(_chain_diff()) == [0.0, 1.0, 2.0]  # the second chain has no head note


def test_nps_series_counts_per_second_bin():
    series = nps_series(_chain_diff(), Timing(120.0, []), 3.0)
    assert series == [2.0, 1.0, 0.0]


def test_notes_after_the_song_end_are_dropped():
    assert nps_series(diff("Expert", [0.0, 100.0]), Timing(120.0, []), 2.0) == [1.0, 0.0]


def test_all_series_lists_only_difficulties_with_notes():
    bm = beatmap(Easy=diff("Easy", []), Expert=diff("Expert", [0.0]))
    assert list(all_series(bm, Timing(120.0, []), 2.0)) == ["Expert"]


def test_mean_nps_weights_partial_bins():
    series = [2.0, 4.0, 6.0, 8.0]
    assert mean_nps(series, 0.0, 4.0) == pytest.approx(5.0)
    assert mean_nps(series, 0.5, 1.5) == pytest.approx(3.0)
    assert mean_nps(series, 3.0, 3.0) == 0.0
    assert peak(series) == 8.0 and peak([]) == 0.0


def test_slope_is_the_least_squares_trend():
    assert slope([1.0, 2.0, 3.0, 4.0], 0.0, 4.0) == pytest.approx(1.0)
    assert slope([3.0, 3.0, 3.0], 0.0, 3.0) == pytest.approx(0.0)
    assert slope([4.0, 3.0, 2.0, 1.0], 0.0, 4.0) == pytest.approx(-1.0)
    assert slope([5.0], 0.0, 1.0) == 0.0
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_crop_nps.py -q`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'saber_tooth.crop.nps'`.

- [ ] **Step 3: Implement**

Create `src/saber_tooth/crop/nps.py`:

```python
"""Notes per second per difficulty, in 1 s steps."""

import math

from saber_tooth.model import DIFFICULTIES, Beatmap, Difficulty
from saber_tooth.timing import Timing


def note_beats(d: Difficulty) -> list[float]:
    """Beat of every counted note, ascending. Bombs and arcs add none; a chain adds its head
    only, and only when its head is not already one of the difficulty's notes."""
    heads = {(round(n.beat, 6), n.x, n.y, int(n.color)) for n in d.notes}
    beats = [n.beat for n in d.notes]
    for chain in d.raw.get("burstSliders", []):
        try:
            key = (round(float(chain["b"]), 6), int(chain["x"]), int(chain["y"]), int(chain["c"]))
        except (KeyError, TypeError, ValueError):
            continue
        if key not in heads:
            heads.add(key)
            beats.append(key[0])
    return sorted(beats)


def nps_series(d: Difficulty, timing: Timing, duration_s: float) -> list[float]:
    counts = [0.0] * max(1, math.ceil(duration_s))
    for beat in note_beats(d):
        i = int(timing.to_seconds(beat))
        if 0 <= i < len(counts):
            counts[i] += 1.0
    return counts


def all_series(beatmap: Beatmap, timing: Timing, duration_s: float) -> dict[str, list[float]]:
    return {
        name: nps_series(beatmap.difficulties[name], timing, duration_s)
        for name in DIFFICULTIES
        if name in beatmap.difficulties and beatmap.difficulties[name].notes
    }


def peak(series: list[float]) -> float:
    return max(series, default=0.0)


def mean_nps(series: list[float], start_s: float, end_s: float) -> float:
    """Mean notes per second over [start_s, end_s), partial bins weighted by overlap."""
    if end_s <= start_s:
        return 0.0
    total = 0.0
    for i in range(max(0, int(start_s)), min(len(series), math.ceil(end_s))):
        overlap = min(end_s, i + 1) - max(start_s, i)
        if overlap > 0:
            total += series[i] * overlap
    return total / (end_s - start_s)


def slope(series: list[float], start_s: float, end_s: float) -> float:
    """Least-squares slope of the bins whose centre lies in [start_s, end_s); 0 under two bins."""
    lo = max(0, math.ceil(start_s - 0.5))
    hi = min(len(series), math.ceil(end_s - 0.5))
    ys = series[lo:hi]
    n = len(ys)
    if n < 2:
        return 0.0
    mean_x, mean_y = (n - 1) / 2, sum(ys) / n
    num = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(ys))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_crop_nps.py -q`
Expected: 6 passed.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/crop/nps.py tests/test_crop_nps.py && uv run ruff format --check src/saber_tooth/crop/nps.py tests/test_crop_nps.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: crop notes per second series"` (subagents never commit).

---
