### Task 5 (Lane A): Check rules

**Files:**

- Create: `src/saber_tooth/checks/__init__.py` (registry + `run_checks`), `checks/finding.py`, `checks/flow.py` (parity-break, wide-jump, swing-speed), `checks/layout.py` (stack-conflict, crossover, vision-block, note-in-wall), `checks/structure.py` (missing-difficulty, default-environment)
- Test: `tests/test_checks_flow.py`, `tests/test_checks_layout.py`, `tests/test_checks_structure.py`

**Interfaces:**

- Consumes: Tasks 2-4.
- Produces: `Finding(rule: str, difficulty: str, beat_start: float, beat_end: float, severity: Literal["error","warn"], message: str, notes: tuple[Note, ...])` (frozen, `to_dict()`); `Analysis` placeholder import from Task 6 is optional (`analysis: Analysis | None = None`); `run_checks(beatmap: Beatmap, analysis=None, rules: set[str] | None = None, difficulty: str | None = None) -> list[Finding]`; `check_difficulty(d: Difficulty, timing: Timing, profile: Profile, analysis=None) -> list[Finding]`. Rule ids: `parity-break, wide-jump, swing-speed, stack-conflict, crossover, vision-block, note-in-wall, empty-gap, missing-difficulty, default-environment`.

Severity rule for every measured rule: a value beyond `profile.error` gives `error`; beyond `profile.warn` only gives `warn`; otherwise no finding. Timing for a difficulty: `Timing(info.bpm, d.bpm_events)`.

Rule definitions (consecutive swings `a`, `b` of one hand, `dt = b.seconds - a.seconds`):

1. `parity-break`: both vectors known, `dot(a.vector, b.vector) > 0.1`, no bomb between them in the hand's half (x 0-1 red, 2-3 blue, either for centre bombs at x 1-2), and `dt < reset_window_s`.
2. `wide-jump`: distance from `a.end` to `b.start` in cells divided by `dt` exceeds `max_hand_speed`.
3. `swing-speed`: `dt < min_hand_gap_s`.
4. `stack-conflict`: within one swing, (a) notes have non-ANY cuts whose vectors differ by more than 45 degrees, or (b) any two notes are more than 1.5 cells apart (the user's "same colour blocks on separate parts of the screen"), or (c) the line between the two farthest notes is more than 45 degrees off the swing vector. Always `error`.
5. `crossover`: a red note and a blue note within `cross_window_s` where `red.x - blue.x >= 2` and both are on the far side (red x >= 2, blue x <= 1), or `red.x > blue.x` at the same beat with matching rows. `error` when inside `error.cross_window_s`, else `warn`.
6. `vision-block`: a note at `x in (1, 2), y == 1` followed by any other note within `(0.05, vision_window_s]` seconds whose position is not the same cell.
7. `note-in-wall`: note whose `x in [w.x, w.x + w.width)`, `y in [w.y, w.y + w.height)` and beat within `[w.beat, w.beat + w.duration]`. Always `error`.
8. `missing-difficulty`: for each name in `DIFFICULTIES` absent from the map; `difficulty` field is that name; `error`.
9. `default-environment`: `info.environment == "DefaultEnvironment"` or no difficulty has events or box groups; `warn`; `difficulty` field `"*"`.

- [ ] **Step 1: Write failing tests** (one valid and one invalid case per rule; example for the user's case and parity):

```python
from saber_tooth.model import Note, Color, Cut, Difficulty
from saber_tooth.timing import Timing
from saber_tooth.profiles import PROFILES
from saber_tooth.checks import check_difficulty

T = Timing(120.0, [])


def rules(notes, name="Expert"):
    d = Difficulty(name, 16, 0, notes=sorted(notes))
    return {(f.rule, f.severity) for f in check_difficulty(d, T, PROFILES[name])}


def test_split_same_colour_is_error():
    ns = [Note(4.0, 0, 0, Color.RED, Cut.DOWN), Note(4.0, 3, 2, Color.RED, Cut.DOWN)]
    assert ("stack-conflict", "error") in rules(ns)


def test_clean_alternation_has_no_findings():
    ns = []
    for i in range(16):
        cut = Cut.DOWN if i % 2 == 0 else Cut.UP
        ns.append(Note(4.0 + i, 1, 0, Color.RED, cut))
        ns.append(Note(4.0 + i, 2, 0, Color.BLUE, cut))
    assert rules(ns) == set()


def test_double_down_fast_is_parity_error():
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.5, 1, 0, Color.RED, Cut.DOWN)]
    assert ("parity-break", "error") in rules(ns)


def test_far_jump_in_quarter_beat_is_error():
    ns = [Note(4.0, 0, 0, Color.RED, Cut.DOWN), Note(4.25, 3, 2, Color.RED, Cut.UP)]
    assert ("wide-jump", "error") in rules(ns)


def test_bomb_reset_allows_same_direction():
    from saber_tooth.model import Bomb

    d = Difficulty(
        "Expert",
        16,
        0,
        notes=[Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(5.0, 1, 0, Color.RED, Cut.DOWN)],
        bombs=[Bomb(4.5, 1, 2)],
    )
    assert not [f for f in check_difficulty(d, T, PROFILES["Expert"]) if f.rule == "parity-break"]
```

Add analogous valid/invalid pairs for `swing-speed`, `crossover`, `vision-block`, `note-in-wall`, `missing-difficulty`, `default-environment`.

- [ ] **Step 2:** Run, expect FAIL. **Step 3:** Implement rules as pure functions `rule(d, swings, timing, profile) -> list[Finding]`, registered in `RULES: dict[str, Callable]`. **Step 4:** Run, expect pass.
- [ ] **Step 5:** Commit `feat: add playability check rules`.
