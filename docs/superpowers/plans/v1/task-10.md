### Task 10: Fixer (proposals from findings)

**Files:**

- Create: `src/saber_tooth/fixer/__init__.py`, `fixer/ops.py`, `fixer/strategies.py`
- Test: `tests/test_fixer.py`

**Interfaces:**

- Consumes: Tasks 2-6, 8, 12.
- Produces:
  - Ops (frozen dataclasses with `to_dict`/`from_dict`): `Move(difficulty, note, x, y, cut)`, `Recolor(difficulty, note)`, `Flip(difficulty, note, cut)`, `Delete(difficulty, note)`, `Fill(difficulty, beat_start, beat_end, notes: tuple[Note, ...])`, `AddDifficulty(difficulty: Difficulty)`, `ApplyLightshow(environment: str, color_scheme: ColorScheme | None, events: dict[str, tuple[list[BasicEvent], list[tuple[float,bool]], dict[str, list]]])`.
  - `apply_ops(beatmap: Beatmap, ops: list[Op]) -> Beatmap` (pure, returns a deep copy).
  - `Proposal(rule, difficulty, severity, summary, ops: list[Op], before: list[Note], after: list[Note])`.
  - `propose(beatmap: Beatmap, finding: Finding, analysis: Analysis | None, templates: Templates | None, seed: int) -> Proposal | None`.

Strategy order per rule; each candidate is accepted only when re-running `check_difficulty` on the result removes the finding and adds no finding that was not present before (compare by `(rule, beat_start, beat_end)`):

1. `parity-break`: Flip second swing's notes to the opposite of the previous vector; then the two 45-degree neighbours; then Delete the second swing.
2. `wide-jump`: Move the second swing toward `a.end`, nearest cells first; then Delete.
3. `swing-speed`: Delete the note with the lower candidate score (later note when no analysis).
4. `stack-conflict`: Move outlying notes adjacent along the swing line; then Delete the outliers.
5. `crossover`: Recolor both notes (swap colours) with flipped cuts if needed; then Move; then Delete the later note.
6. `vision-block`: Move the blocking note outward (x 1 to 0, x 2 to 3) same row; then to row 0.
7. `note-in-wall`: Move to the nearest free lane; then Delete.
8. `empty-gap`: Fill with `generate_difficulty(..., window=(start, end), entry=last swings before the gap)`, target density = mean of the 8 beats on either side.
9. `missing-difficulty`: AddDifficulty with `generate_difficulty` when analysis exists; without analysis, thin the nearest denser difficulty by keeping the highest-scoring notes per bar to the profile's target and re-flowing cuts; if no denser difficulty exists, return `None` with reason "needs analysis".
10. `default-environment`: ApplyLightshow from Task 12.

- [ ] **Step 1: Write failing tests**

```python
from hypothesis import given, settings, strategies as st
from saber_tooth.model import Note, Color, Cut, Difficulty, Beatmap, MapInfo
from saber_tooth.checks import check_difficulty, run_checks
from saber_tooth.fixer import propose, apply_ops


def bm(notes):
    info = MapInfo("s", "", "a", "m", 120.0, "song.egg", "cover.png", 0, 10, "NiceEnvironment")
    return Beatmap(info, {"Expert": Difficulty("Expert", 16, 0, notes=sorted(notes))})


def test_split_stack_fixed():
    m = bm([Note(4.0, 0, 0, Color.RED, Cut.DOWN), Note(4.0, 3, 2, Color.RED, Cut.DOWN)])
    f = next(f for f in run_checks(m, difficulty="Expert") if f.rule == "stack-conflict")
    p = propose(m, f, None, None, 1)
    fixed = apply_ops(m, p.ops)
    assert not [g for g in run_checks(fixed, difficulty="Expert") if g.rule == "stack-conflict"]


notes = st.builds(
    Note,
    beat=st.integers(8, 200).map(lambda i: i / 4),
    x=st.integers(0, 3),
    y=st.integers(0, 2),
    color=st.sampled_from(Color),
    cut=st.sampled_from([c for c in Cut if c != Cut.ANY]),
)


@settings(max_examples=60, deadline=None)
@given(st.lists(notes, min_size=2, max_size=30))
def test_fix_removes_finding_and_adds_none(ns):
    m = bm(ns)
    before = {
        (f.rule, f.beat_start, f.beat_end)
        for f in run_checks(
            m,
            rules={
                "parity-break",
                "wide-jump",
                "swing-speed",
                "stack-conflict",
                "crossover",
                "vision-block",
            },
        )
    }
    for f in run_checks(
        m,
        rules={
            "parity-break",
            "wide-jump",
            "swing-speed",
            "stack-conflict",
            "crossover",
            "vision-block",
        },
    ):
        p = propose(m, f, None, None, 1)
        if p is None:
            continue
        after = {
            (g.rule, g.beat_start, g.beat_end)
            for g in run_checks(apply_ops(m, p.ops), rules={r for r, *_ in before} | {f.rule})
        }
        assert (f.rule, f.beat_start, f.beat_end) not in after
        assert after <= before
```

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add fix proposals with verified strategies`.
