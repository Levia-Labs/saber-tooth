# Task 3: Pitched tracks in the analyser reader

The spec's change score needs bass, chord and melody onsets. `Analysis` (`analysis.py:10-18`) holds only beats, kick, snare and hh, and `read_project` (`analysis.py:28-40`) ignores `bass.csv`, `chords.csv` and `melody.csv`, which beat-analyser writes (ADR 0005: header-less `time,label_id`). New fields have defaults, so every existing positional `Analysis(...)` call keeps working.

**Files:**

- Modify: `src/saber_tooth/analysis.py`
- Test: `tests/test_analysis_pitched.py`

**Interfaces:**

Consumes: `read_project(folder: Path) -> Analysis`.

Produces: `Analysis` gains `bass: list[float]`, `chords: list[float]`, `melody: list[float]` (onset seconds, ascending) and `melody_ids: list[int]` (label id per melody onset, same order; a pitch proxy, 0 when the cell is missing or not numeric); all default to `[]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_analysis_pitched.py`:

```python
import json
from pathlib import Path

from saber_tooth.analysis import Analysis, read_project

SONG1 = Path(__file__).parent / "fixtures" / "analyser" / "song1"


def test_pitched_tracks_are_read_in_time_order(tmp_path):
    (tmp_path / "meta.json").write_text(
        json.dumps({"name": "p", "key": "C", "bpm": 120}), encoding="utf-8"
    )
    (tmp_path / "bass.csv").write_text("1.0,3\n0.5,4\n", encoding="utf-8")
    (tmp_path / "chords.csv").write_text("2.0,1\n", encoding="utf-8")
    (tmp_path / "melody.csv").write_text("3.0,60\n1.0,55\n2.0,x\n", encoding="utf-8")
    a = read_project(tmp_path)
    assert a.bass == [0.5, 1.0] and a.chords == [2.0]
    assert a.melody == [1.0, 2.0, 3.0] and a.melody_ids == [55, 0, 60]


def test_missing_or_empty_pitched_files_give_empty_lists():
    a = read_project(SONG1)
    assert a.bass == [] and a.chords == [] and a.melody == [] and a.melody_ids == []


def test_existing_positional_construction_still_works():
    a = Analysis("x", "k", 120.0, [], [0.0], [], [], None)
    assert a.bass == [] and a.melody_ids == []
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_analysis_pitched.py -q`
Expected: FAIL: `AttributeError: 'Analysis' object has no attribute 'bass'`.

- [ ] **Step 3: Implement**

In `src/saber_tooth/analysis.py` change the import line `from dataclasses import dataclass` to:

```python
from dataclasses import dataclass, field
```

Replace the `Analysis` class with:

```python
@dataclass(frozen=True)
class Analysis:
    name: str
    key: str
    bpm: float
    beats: list[float]
    kick: list[float]
    snare: list[float]
    hh: list[float]
    audio: Path | None
    bass: list[float] = field(default_factory=list)
    chords: list[float] = field(default_factory=list)
    melody: list[float] = field(default_factory=list)
    melody_ids: list[int] = field(default_factory=list)  # label id per melody onset
```

Add after `_times`:

```python
def _labelled(path: Path) -> list[tuple[float, int]]:
    """(time, label id) rows sorted by time; a missing or non-numeric label reads as 0."""
    if not path.is_file():
        return []
    rows: list[tuple[float, int]] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                label = int(float(row[1])) if len(row) > 1 else 0
            except ValueError:
                label = 0
            rows.append((float(row[0]), label))
    return sorted(rows)
```

Replace `read_project` with:

```python
def read_project(folder: Path) -> Analysis:
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    audio = folder / "audio.wav"
    melody = _labelled(folder / "melody.csv")
    return Analysis(
        name=str(meta["name"]),
        key=str(meta["key"]),
        bpm=float(meta["bpm"]),
        beats=_times(folder / "beats.csv"),
        kick=_times(folder / "kick.csv"),
        snare=_times(folder / "snare.csv"),
        hh=_times(folder / "hh.csv"),
        audio=audio if audio.is_file() else None,
        bass=_times(folder / "bass.csv"),
        chords=_times(folder / "chords.csv"),
        melody=[t for t, _ in melody],
        melody_ids=[label for _, label in melody],
    )
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_analysis_pitched.py tests/test_analysis.py tests/test_generator.py -q`
Expected: all pass (the generator tests build `Analysis` positionally).

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/analysis.py tests/test_analysis_pitched.py && uv run ruff format --check src/saber_tooth/analysis.py tests/test_analysis_pitched.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: read bass, chord and melody tracks from the analyser"` (subagents never commit).

---
