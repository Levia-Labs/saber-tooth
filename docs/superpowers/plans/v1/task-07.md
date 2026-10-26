### Task 7 (Lane A): CLI check, inspect, survey

**Files:**

- Create: `src/saber_tooth/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**

- Produces: `main(argv: list[str] | None = None) -> int`. Subcommands:

  - `check <folder> [--json]`: prints one line per rule and difficulty with error and warning counts plus a total line, at most 20 lines; `--json` prints findings as JSON.
  - `inspect <folder>`: title, mapper, bpm, environment, difficulties with note counts and NPS.
  - `survey <levels_dir>`: one line per rule with total error and warning counts and the number of maps affected, plus `parse_errors=N`.
  - `learn <levels_dir> <out.json>` (wired in Task 11).
  - `gen-url <url> [--api http://127.0.0.1:8100]` (wired in Task 16).

- [ ] **Step 1: Write failing test**

```python
from pathlib import Path
from saber_tooth.cli import main

FIX = Path(__file__).parent / "fixtures" / "maps"


def test_check_prints_counts(capsys):
    assert main(["check", str(FIX / "v2_basic")]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1].startswith("total ") and len(out) <= 20


def test_survey(capsys):
    assert main(["survey", str(FIX)]) == 0
    assert "parse_errors=" in capsys.readouterr().out
```

- [ ] **Steps 2-4:** fail, implement with `argparse`, pass. **Step 5:** Commit `feat: add check, inspect and survey CLI`.
