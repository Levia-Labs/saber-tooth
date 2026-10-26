### Task 6 (Lane A): Analysis model and empty-gap rule

**Files:**

- Create: `src/saber_tooth/analysis.py`, `src/saber_tooth/checks/gaps.py`
- Create fixture: `tests/fixtures/analyser/song1/` (`meta.json` `{"name":"song1","key":"A minor","bpm":120.0}`, `beats.csv`, `kick.csv`, `snare.csv`, `hh.csv`, empty `bass.csv`, `melody.csv`, `chords.csv`, no audio)
- Test: `tests/test_analysis.py`, `tests/test_checks_gaps.py`

**Interfaces:**

- Produces: `Analysis(name: str, key: str, bpm: float, beats: list[float], kick: list[float], snare: list[float], hh: list[float], audio: Path | None)` (all times seconds); `read_project(folder: Path) -> Analysis` (CSV columns `time,label_id`, no header; missing CSV gives empty list; `audio` = `folder/"audio.wav"` when present); `onset_density(a: Analysis, start_s: float, end_s: float) -> float` (weighted onsets per second, kick 1.0, snare 0.8, hh 0.3); rule `empty-gap` registered in `RULES`.

`empty-gap`: for each gap between consecutive notes (any colour, plus song start to first note after the first analysed beat, plus last note to the last analysed onset) of at least `profile.gap_beats` beats, if `onset_density >= 1.5` over the gap, emit `warn` with `beat_start`/`beat_end` = gap edges. Skipped when `analysis is None`.

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path
from saber_tooth.analysis import read_project, onset_density, Analysis
from saber_tooth.model import Note, Color, Cut, Difficulty
from saber_tooth.timing import Timing
from saber_tooth.profiles import PROFILES
from saber_tooth.checks import check_difficulty

FIX = Path(__file__).parent / "fixtures" / "analyser" / "song1"


def test_read_project():
    a = read_project(FIX)
    assert a.bpm == 120.0 and a.kick and a.audio is None


def busy(seconds=60):
    k = [i * 0.5 for i in range(seconds * 2)]
    return Analysis("x", "C major", 120.0, k, k, [], k, None)


def test_gap_with_music_is_flagged():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(40.0, 1, 0, Color.RED, Cut.UP)]
    d = Difficulty("Expert", 16, 0, notes=ns)
    f = [
        f
        for f in check_difficulty(d, Timing(120, []), PROFILES["Expert"], busy())
        if f.rule == "empty-gap"
    ]
    assert f and f[0].beat_start == 4.0 and f[0].beat_end == 40.0


def test_gap_in_silence_is_fine():
    quiet = Analysis("x", "C major", 120.0, [i * 0.5 for i in range(120)], [], [], [], None)
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(40.0, 1, 0, Color.RED, Cut.UP)]
    d = Difficulty("Expert", 16, 0, notes=ns)
    assert not [
        f
        for f in check_difficulty(d, Timing(120, []), PROFILES["Expert"], quiet)
        if f.rule == "empty-gap"
    ]
```

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add analysis reader and empty-gap rule`.
