### Task 11 (Lane B): Lightshow learner

**Files:**

- Create: `src/saber_tooth/lightshow/__init__.py`, `lightshow/units.py`, `lightshow/learn.py`
- Create fixture: extend `tests/fixtures/maps/v3_boxes/Expert.dat` with 8 bars of notes and basic events
- Test: `tests/test_lightshow_learn.py`

**Interfaces:**

- Produces: `Unit(environment: str, source: str, energy: float, events: list[BasicEvent], boosts: list[tuple[float,bool]], groups: dict[str, list[dict]])` (all beats relative to bar start, bar length 4 beats); `Templates(units: dict[str, list[Unit]], schemes: dict[str, list[ColorScheme]])` with `save(path)`/`load(path)` JSON; `learn(levels: Path) -> Templates` (read-only; skips parse errors; only maps whose environment is not `DefaultEnvironment` and that have at least 16 basic events or one box group).

Unit extraction: for each bar of the densest difficulty, slice events and box groups whose `b` falls in `[bar, bar+4)`, rebase beats, and set energy = notes in that bar divided by the map's 90th-percentile notes-per-bar (clamped 0..1). Skip bars with no lighting at all. Box-group dicts keep their `g` (group id) and inner `e` lists unchanged apart from rebased `b`.

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path
from saber_tooth.lightshow import learn, Templates

FIX = Path(__file__).parent / "fixtures" / "maps"


def test_learns_units_per_environment(tmp_path):
    t = learn(FIX)
    assert t.units and all(env != "DefaultEnvironment" for env in t.units)
    unit = next(iter(t.units.values()))[0]
    assert all(0 <= e.beat < 4 for e in unit.events)
    t.save(tmp_path / "t.json")
    assert Templates.load(tmp_path / "t.json").units.keys() == t.units.keys()
```

- [ ] **Steps 2-4:** fail, implement, wire CLI `learn`, pass. **Step 5:** Commit `feat: learn vanilla lightshow units from installed maps`.
