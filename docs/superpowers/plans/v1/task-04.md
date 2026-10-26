### Task 4 (Lane A): Difficulty profiles and swing model

**Files:**

- Create: `src/saber_tooth/profiles.py`, `src/saber_tooth/swings.py`
- Test: `tests/test_swings.py`

**Interfaces:**

- Produces: `Limits` (fields `min_hand_gap_s, max_hand_speed, reset_window_s, cross_window_s, vision_window_s`), `Profile` (fields `name, njs, offset, target_nps, grid, allow_doubles, allow_dots, error: Limits, warn: Limits, gap_beats: float`), `PROFILES: dict[str, Profile]`; `Swing(hand: Color, beat: float, seconds: float, notes: tuple[Note, ...], vector: tuple[float, float] | None, start: tuple[float, float], end: tuple[float, float])`; `build_swings(notes: list[Note], timing: Timing, window_s: float = 0.02) -> dict[Color, list[Swing]]`.

Profile table (`error` = impossible threshold for scanning, `warn` = comfort threshold that generated maps must also meet):

| name       | njs | nps | grid | doubles | dots | warn gap/speed/reset/cross/vision | error gap/speed/reset/cross/vision |
| ---------- | --- | --- | ---- | ------- | ---- | --------------------------------- | ---------------------------------- |
| Easy       | 10  | 1.2 | 1.0  | no      | no   | 0.75 / 4 / 1.5 / 0.6 / 0.5        | 0.40 / 7 / 0.8 / 0.35 / 0.30       |
| Normal     | 12  | 2.0 | 0.5  | no      | no   | 0.50 / 5 / 1.2 / 0.5 / 0.45       | 0.30 / 10 / 0.6 / 0.30 / 0.25      |
| Hard       | 14  | 3.2 | 0.5  | yes     | no   | 0.32 / 6.5 / 0.9 / 0.4 / 0.40     | 0.18 / 14 / 0.45 / 0.25 / 0.20     |
| Expert     | 16  | 4.6 | 0.25 | yes     | yes  | 0.22 / 8 / 0.7 / 0.3 / 0.35       | 0.12 / 20 / 0.35 / 0.20 / 0.18     |
| ExpertPlus | 18  | 6.2 | 0.25 | yes     | yes  | 0.16 / 10 / 0.5 / 0.25 / 0.30     | 0.09 / 25 / 0.30 / 0.15 / 0.15     |

`gap_beats = 8.0` for all.

Swing model: notes of one colour within `window_s` seconds form one swing (stacks, windows, sliders heads). Swing vector: the shared cut vector if all non-ANY notes agree, else `None`; for an all-ANY swing infer vector as the opposite of the previous swing's vector (first swing: DOWN). `start`/`end`: grid positions of the first/last note along the vector (sorted by projection onto the vector).

- [ ] **Step 1: Write failing tests**

```python
from saber_tooth.model import Note, Color, Cut
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing

T = Timing(120.0, [])


def test_stack_is_one_swing():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.DOWN), Note(1.0, 1, 1, Color.RED, Cut.DOWN)]
    s = build_swings(ns, T)[Color.RED]
    assert len(s) == 1 and s[0].start == (1, 1) and s[0].end == (1, 0)


def test_dot_infers_opposite():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.DOWN), Note(2.0, 1, 0, Color.RED, Cut.ANY)]
    s = build_swings(ns, T)[Color.RED]
    assert s[1].vector == (0, 1)


def test_hands_split():
    ns = [Note(1.0, 1, 0, Color.RED, Cut.DOWN), Note(1.0, 2, 0, Color.BLUE, Cut.DOWN)]
    s = build_swings(ns, T)
    assert len(s[Color.RED]) == 1 and len(s[Color.BLUE]) == 1
```

- [ ] **Step 2:** Run, expect FAIL. **Step 3:** Implement per the rules above. **Step 4:** Run, expect pass.
- [ ] **Step 5:** Commit `feat: add difficulty profiles and swing model`.
