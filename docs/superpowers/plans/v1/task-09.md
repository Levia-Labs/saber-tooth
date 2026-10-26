### Task 9: Map assembly for new songs

**Files:**

- Create: `src/saber_tooth/assemble.py`
- Test: `tests/test_assemble.py`

**Interfaces:**

- Consumes: Tasks 3, 8, 12.
- Produces: `folder_name(title: str) -> str`; `assemble_new(a: Analysis, templates: Templates | None, out: Path, seed: int, encode: Callable[[Path, Path], None]) -> Beatmap` (writes `song.egg` through `encode(wav, egg)`, `cover.png` via Pillow, Info and five difficulties, lightshow applied when templates exist).

- [ ] **Step 1: Write failing tests**

```python
from saber_tooth.assemble import folder_name


def test_folder_name_sanitized():
    assert (
        folder_name('AC/DC: Back?In "Black"')
        == "st-acdc-backin-black (ACDC BackIn Black - saber-tooth)"
    )
```

Plus `test_assemble_writes_five_difficulties(tmp_path)` using the Task 6 fixture with a fake `encode` that copies bytes, asserting `load_map(out)` has five difficulties, `song.egg` and `cover.png` exist, and no difficulty has findings.

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: assemble generated maps into folders`.
