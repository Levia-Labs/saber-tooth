### Task 8: Tempo map and generator

**Files:**

- Create: `src/saber_tooth/generator/__init__.py`, `generator/tempo.py`, `generator/candidates.py`, `generator/motifs.py`, `generator/placer.py`
- Test: `tests/test_generator.py`

**Interfaces:**

- Consumes: Tasks 2-6.
- Produces:
  - `tempo_map(a: Analysis) -> tuple[float, list[BpmEvent]]`: base bpm and events so that map beat `phase + k` lands on `a.beats[k]`; emits an event only where local bpm differs from the current one by more than 0.5 percent.
  - `generate_difficulty(a: Analysis, timing: Timing, profile: Profile, seed: int, window: tuple[float, float] | None = None, entry: dict[Color, Swing] | None = None) -> Difficulty`.
  - `generate_all(a: Analysis, seed: int) -> tuple[Timing, dict[str, Difficulty]]`.

Algorithm (quality bar: flowing and musical):

1. Candidates (`candidates.py`): every onset converted to beats and snapped to `profile.grid`, scored kick 1.0, snare 0.9, hh 0.4, plus 0.3 when on a whole beat and 0.2 on a bar start (beat % 4 == 0). Merge duplicates keeping the max score.
2. Energy per bar: `onset_density` over the bar normalised by the song's 90th-percentile bar. Target notes per bar = `target_nps * bar_seconds * (0.5 + energy)`, capped by the grid.
3. Selection: per bar, take the highest-scoring candidates up to the target, then drop any that would break `profile.warn.min_hand_gap_s` given alternating hands.
4. Hand assignment: alternate hands; on bar starts with kick score and energy > 0.7, place a double (both hands) when `allow_doubles`.
5. Motifs (`motifs.py`): a library of 4-swing sequences per hand of `(cut, x, y)` that respect parity and reach: for red, `[(DOWN,1,0),(UP,1,0),(DOWN_LEFT,0,0),(UP_RIGHT,1,1)]`, `[(DOWN,1,0),(UP_LEFT,0,1),(DOWN_RIGHT,1,0),(UP,1,0)]`, `[(DOWN_LEFT,1,0),(UP_RIGHT,1,1),(DOWN,1,0),(UP,0,0)]`, and more (at least 8); blue motifs are the mirror (`x -> 3 - x`, LEFT and RIGHT swapped). Each 4-bar phrase picks one motif per hand with `random.Random(seed + phrase)` and repeats it, mirroring vertically on the second half of the phrase for variety. This follows musical phrasing instead of a fixed grid.
6. Placement (`placer.py`): walk the selected times; for each hand take the next motif step, then verify against the previous swing: parity (dot < 0), `warn.max_hand_speed`, no crossover, no vision block (never place x 1-2, y 1 in Expert and below; ExpertPlus allows it only when the next note is more than `warn.vision_window_s` away). If the step fails, try the other motifs' steps whose cut is opposite the previous swing; if all fail, drop the note.
7. Dots (`Cut.ANY`) are never generated. Bombs and walls are never generated in v1.
8. NJS and offset from profile.
9. After placement run `check_difficulty`; any remaining finding raises `GenerationError` (a bug, caught by tests).

- [ ] **Step 1: Write failing tests**

```python
from hypothesis import given, settings, strategies as st
from saber_tooth.analysis import Analysis
from saber_tooth.generator import generate_all, tempo_map
from saber_tooth.checks import check_difficulty
from saber_tooth.profiles import PROFILES
from saber_tooth.model import DIFFICULTIES


def synth(bpm, seconds, swing):
    spb = 60.0 / bpm
    beats = [i * spb for i in range(int(seconds / spb))]
    kick = beats[::2]
    snare = beats[1::2]
    hh = [b + spb / 2 * (1 + swing) for b in beats]
    return Analysis("s", "A minor", bpm, beats, kick, snare, hh, None)


@settings(max_examples=25, deadline=None)
@given(st.floats(70, 200), st.integers(30, 180), st.floats(0, 0.3), st.integers(0, 1000))
def test_generated_maps_have_zero_findings(bpm, seconds, swing, seed):
    a = synth(bpm, seconds, swing)
    timing, diffs = generate_all(a, seed)
    assert set(diffs) == set(DIFFICULTIES)
    for name, d in diffs.items():
        assert check_difficulty(d, timing, PROFILES[name], a) == []


def test_density_increases_with_difficulty():
    timing, diffs = generate_all(synth(128, 120, 0.0), 7)
    counts = [len(diffs[n].notes) for n in DIFFICULTIES]
    assert counts == sorted(counts) and counts[0] < counts[-1]


def test_tempo_map_aligns_beats():
    a = synth(120, 30, 0.0)
    a.beats[:] = [0.3 + b for b in a.beats]
    from saber_tooth.timing import Timing

    bpm, events = tempo_map(a)
    t = Timing(bpm, events)
    assert abs(t.to_seconds(t.to_beats(a.beats[10])) - a.beats[10]) < 1e-6
```

Note: `empty-gap` must also stay clean, so selection guarantees at least one note every `gap_beats - 1` beats while onset density is at least 1.5.

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add rule-based flowing map generator`.
