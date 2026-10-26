# saber-tooth v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Docker service (FastAPI API + plain HTML frontend) that generates Beat Saber maps from beat-analyser output, finds and fixes impossible and empty sections, adds missing difficulties and applies learned vanilla lightshows, writing only new map folders after per-change approval.

**Architecture:** One Python package `saber_tooth` with pure cores (`model`, `timing`, `mapio`, `profiles`, `swings`, `checks`, `generator`, `fixer`, `lightshow`) and thin shells (`store`, `analyser`, `jobs`, `api`, `web`, `cli`). Cores never touch the network or the real `CustomLevels`; shells are tested with temp dirs and `httpx.MockTransport`. Compose runs saber-tooth next to the `levialabs/beat-analyser` image with a shared uploads volume.

**Tech Stack:** Python 3.12, uv, FastAPI, uvicorn, httpx, Pillow, pytest, hypothesis, ruff, SQLite (stdlib), ffmpeg (container), vanilla JS, Taskfile, Crepidoma.

**Spec:** `docs/superpowers/specs/2026-10-26-saber-tooth-design.md`

## Global Constraints

1. Vanilla only: never emit Chroma, Noodle Extensions, Vivify, Heck keys, `_requirements` or `_suggestions` entries. Source maps keep theirs untouched only in the copied original files we do not rewrite.
2. Output: difficulty files `version: "3.3.0"`, Info `_version: "2.1.0"`. Standard characteristic only.
3. Every saber-tooth output map has all five Standard difficulties: Easy, Normal, Hard, Expert, ExpertPlus.
4. Never write inside an existing map folder. New folders only, created via `.partial` folder then rename.
5. Fixed-map folder name: `<original folder name> [saber-tooth]`, then `[saber-tooth 2]`, `[saber-tooth 3]` on repeats. Info `_songName` gets suffix ` [saber-tooth]`.
6. Generated-map folder name: `st-<slug> (<Title> - saber-tooth)` with characters `<>:"/\|?*` removed.
7. Quality bar: generated difficulties have zero findings (errors and warnings). Applied fixes leave zero errors and add no new finding.
8. Source files at most 300 lines. Python text I/O passes `encoding="utf-8"`. LF line endings. No em dashes.
9. Tests never read the real `CustomLevels` or call real services.
10. Service binds `127.0.0.1` only; port `${SABER_PORT:-8100}`.

## Review Focus

1. Map folder using lowercase `info.dat` and `ExpertPlusStandard.dat` / `Hard.beatmap.dat` names must load (Task 3 test `test_discovers_mixed_case_names`).
2. Map with BPM changes (v2 `_customData._BPMChanges`, v3 `bpmEvents`) must time notes in seconds correctly so speed rules do not misfire (Task 2 test `test_timing_with_bpm_change`, Task 3 test `test_v2_bpm_changes_loaded`).
3. Applying fixes to the same map twice must create `[saber-tooth 2]`, never overwrite (Task 15 test `test_apply_twice_creates_numbered_folder`).
4. Two approved proposals that together create a new finding must abort apply, write nothing and name the proposals (Task 15 test `test_conflicting_proposals_abort`).
5. Song title with `:`/`?`/`/` must yield a valid folder name (Task 9 test `test_folder_name_sanitized`).

## Execution lanes

Tasks 1-3 run sequentially. Then three parallel lanes on disjoint paths: Lane A (Tasks 4-7), Lane B (Tasks 11-12, needs only Tasks 2-3 and Task 6's `onset_density`, so it starts after Task 6 lands), Lane C (Tasks 13-14). Then Task 8, then Tasks 9 and 10 in parallel, then 15, then 16 and 17 in parallel, then 18.

`write_map` copies audio and cover only when present in `copy_from`; fixtures carry no audio.

---

### Task 1: Crepidoma adoption and repo scaffold

**Agent:** `crepidoma:pillar-migrator` for steps 1-3, then main thread for steps 4-8.

**Files:**
- Create: `.gitmodules`, `.crepidoma/` (submodule), `Taskfile.yml`, `tasks/Taskfile.yml`, `.claude/settings.json`, `.claude/README.md`, `.pre-commit-config.yaml`, `CLAUDE.md`, `pyproject.toml`, `src/saber_tooth/__init__.py`, `tests/__init__.py`, `tests/test_smoke.py`, `.env.example`, `.gitattributes`
- Modify: `.gitignore`, `README.md`

- [ ] **Step 1:** Create branch `feat/v1` from `main`.
- [ ] **Step 2:** Follow `X:\Projects\Crepidoma\docs\migration.md` steps 1-10 with `X:\Projects\beat-analyser` as the reference: submodule at `.crepidoma`, Taskfile includes from `templates/Taskfile.includes.yml` (claude, lint, repo, todo, git, graph, test, quality, security, ci, rtk, setup; no `go`), settings from `templates/settings.json` (plugin `crepidoma@levia-labs`, `"model": "claude-opus-5-5"`, env `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`), `.pre-commit-config.yaml`, `CLAUDE.md` from template.
- [ ] **Step 3:** Add `tasks/Taskfile.yml` included as namespace `st` with `vars: { PY: "{{.PY}}" }`:

```yaml
version: "3"
tasks:
  test:
    desc: Run the pytest suite. Usage: task st:test [-- <pytest args>]
    cmds: ["uv run pytest -q {{.CLI_ARGS}}"]
  check:
    desc: Run quality checks on one map folder. Usage: task st:check -- <folder>
    cmds: ["uv run saber-tooth check {{.CLI_ARGS}}"]
  inspect:
    desc: Summarise one map folder. Usage: task st:inspect -- <folder>
    cmds: ["uv run saber-tooth inspect {{.CLI_ARGS}}"]
  survey:
    desc: Read-only finding counts across a levels dir. Usage: task st:survey -- <levels_dir>
    cmds: ["uv run saber-tooth survey {{.CLI_ARGS}}"]
  learn:
    desc: Build lightshow templates. Usage: task st:learn -- <levels_dir> <out.json>
    cmds: ["uv run saber-tooth learn {{.CLI_ARGS}}"]
  up:
    desc: Build and start the compose stack. Usage: task st:up
    cmds: ["docker compose up -d --build"]
  down:
    desc: Stop the compose stack. Usage: task st:down
    cmds: ["docker compose down"]
  logs:
    desc: Tail saber-tooth logs. Usage: task st:logs
    cmds: ["docker compose logs --tail 100 saber-tooth"]
  gen:
    desc: Start a map generation job from a URL. Usage: task st:gen -- <url>
    cmds: ["uv run saber-tooth gen-url {{.CLI_ARGS}}"]
```

- [ ] **Step 4:** `pyproject.toml`:

```toml
[project]
name = "saber-tooth"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.32", "httpx>=0.27", "pillow>=11", "python-multipart>=0.0.12"]

[project.scripts]
saber-tooth = "saber_tooth.cli:main"

[dependency-groups]
dev = ["pytest>=8", "hypothesis>=6.100", "ruff>=0.7"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/saber_tooth"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 110
target-version = "py312"
```

- [ ] **Step 5:** `tests/test_smoke.py`: `def test_import(): import saber_tooth`. Run `uv sync` then `uv run pytest -q`. Expected: 1 passed.
- [ ] **Step 6:** `.env.example` with `LEVELS_DIR=X:/SteamLibrary/steamapps/common/Beat Saber/Beat Saber_Data/CustomLevels`, `SABER_PORT=8100`, `YT_MAX_MINUTES=20`, `MAX_UPLOAD_MB=200`. `.gitattributes`: `* text=auto eol=lf`. `.gitignore`: `.env`, `.venv/`, `data/`, `__pycache__/`.
- [ ] **Step 7:** Docs (normal prose, humanizer pass): `README.md` (purpose, quick start `task st:up`, tasks index), `TODO.md`, `docs/architecture.md`, `docs/map-format.md` (v2/v3/v4 key tables from Task 3), `docs/api.md` (routes from spec), `docs/adr/0001-vanilla-only-visuals.md` through `0006-single-process-fastapi-sqlite.md` (Context, Decision, Consequences each), `.claude/README.md` listing agents, skills and plugins, `.claude/agents/map-auditor.md` (haiku; runs `task st:check -- <folder>`, returns at most 10 lines of counts per rule), `.claude/agents/lightshow-learner.md` (sonnet; runs `task st:learn`, reports per-environment unit counts).
- [ ] **Step 8:** Commit: `task git:commit -- "chore: adopt Crepidoma and scaffold saber-tooth"`.

---

### Task 2: Core model and timing

**Files:**
- Create: `src/saber_tooth/model.py`, `src/saber_tooth/timing.py`
- Test: `tests/test_timing.py`

**Interfaces:**
- Produces: `Color`, `Cut`, `Note`, `Bomb`, `Wall`, `BasicEvent`, `BpmEvent`, `Difficulty`, `ColorScheme`, `MapInfo`, `Beatmap`, `DIFFICULTIES`, `CUT_VECTORS`; `Timing(bpm: float, changes: list[BpmEvent])` with `.to_seconds(beat) -> float`, `.to_beats(seconds) -> float`.

- [ ] **Step 1: Write the failing test**

```python
from hypothesis import given, strategies as st
from saber_tooth.model import BpmEvent
from saber_tooth.timing import Timing

def test_constant_bpm():
    t = Timing(120.0, [])
    assert t.to_seconds(4.0) == 2.0
    assert t.to_beats(2.0) == 4.0

def test_timing_with_bpm_change():
    t = Timing(120.0, [BpmEvent(beat=4.0, bpm=60.0)])
    assert t.to_seconds(4.0) == 2.0
    assert t.to_seconds(5.0) == 3.0
    assert t.to_beats(3.0) == 5.0

@given(st.floats(min_value=0, max_value=2000), st.floats(min_value=40, max_value=400))
def test_round_trip(beat, bpm):
    t = Timing(bpm, [BpmEvent(beat=16.0, bpm=bpm * 1.5)])
    assert abs(t.to_beats(t.to_seconds(beat)) - beat) < 1e-6
```

- [ ] **Step 2:** Run `uv run pytest tests/test_timing.py -v`. Expected: FAIL, `ModuleNotFoundError`.
- [ ] **Step 3: Implement**

```python
# model.py
from dataclasses import dataclass, field
from enum import IntEnum

DIFFICULTIES = ("Easy", "Normal", "Hard", "Expert", "ExpertPlus")
RANKS = {"Easy": 1, "Normal": 3, "Hard": 5, "Expert": 7, "ExpertPlus": 9}

class Color(IntEnum):
    RED = 0
    BLUE = 1

class Cut(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    UP_LEFT = 4
    UP_RIGHT = 5
    DOWN_LEFT = 6
    DOWN_RIGHT = 7
    ANY = 8

# Unit swing vectors in grid space (x right, y up); ANY has no direction.
CUT_VECTORS: dict[Cut, tuple[float, float]] = {
    Cut.UP: (0, 1), Cut.DOWN: (0, -1), Cut.LEFT: (-1, 0), Cut.RIGHT: (1, 0),
    Cut.UP_LEFT: (-0.7071, 0.7071), Cut.UP_RIGHT: (0.7071, 0.7071),
    Cut.DOWN_LEFT: (-0.7071, -0.7071), Cut.DOWN_RIGHT: (0.7071, -0.7071),
}
OPPOSITE = {Cut.UP: Cut.DOWN, Cut.DOWN: Cut.UP, Cut.LEFT: Cut.RIGHT, Cut.RIGHT: Cut.LEFT,
            Cut.UP_LEFT: Cut.DOWN_RIGHT, Cut.DOWN_RIGHT: Cut.UP_LEFT,
            Cut.UP_RIGHT: Cut.DOWN_LEFT, Cut.DOWN_LEFT: Cut.UP_RIGHT, Cut.ANY: Cut.ANY}

@dataclass(frozen=True, order=True)
class Note:
    beat: float
    x: int
    y: int
    color: Color
    cut: Cut
    angle: int = 0

@dataclass(frozen=True, order=True)
class Bomb:
    beat: float
    x: int
    y: int

@dataclass(frozen=True, order=True)
class Wall:
    beat: float
    x: int
    y: int
    duration: float
    width: int
    height: int

@dataclass(frozen=True, order=True)
class BasicEvent:
    beat: float
    type: int
    value: int
    float_value: float = 1.0

@dataclass(frozen=True, order=True)
class BpmEvent:
    beat: float
    bpm: float

@dataclass
class Difficulty:
    name: str
    njs: float
    offset: float
    notes: list[Note] = field(default_factory=list)
    bombs: list[Bomb] = field(default_factory=list)
    walls: list[Wall] = field(default_factory=list)
    events: list[BasicEvent] = field(default_factory=list)
    boosts: list[tuple[float, bool]] = field(default_factory=list)
    bpm_events: list[BpmEvent] = field(default_factory=list)
    # Raw v3 lists kept verbatim: event box groups, sliders, burst sliders.
    raw: dict[str, list] = field(default_factory=dict)
    filename: str = ""

@dataclass(frozen=True)
class ColorScheme:
    id: str
    colors: dict[str, dict[str, float]]  # saberAColor, saberBColor, environmentColor0, ... -> {r,g,b,a}

@dataclass
class MapInfo:
    song_name: str
    sub_name: str
    author: str
    mapper: str
    bpm: float
    song_file: str
    cover_file: str
    preview_start: float
    preview_duration: float
    environment: str
    color_scheme: ColorScheme | None = None

@dataclass
class Beatmap:
    info: MapInfo
    difficulties: dict[str, Difficulty]
    folder_name: str = ""
```

```python
# timing.py
from saber_tooth.model import BpmEvent

class Timing:
    """Beat <-> seconds conversion with piecewise-constant tempo."""

    def __init__(self, bpm: float, changes: list[BpmEvent]):
        segs = [BpmEvent(0.0, bpm)] + sorted(c for c in changes if c.beat > 0)
        self._segs: list[tuple[float, float, float]] = []  # (start_beat, start_s, bpm)
        start_s = 0.0
        for i, seg in enumerate(segs):
            if i:
                prev_beat, prev_s, prev_bpm = self._segs[-1]
                start_s = prev_s + (seg.beat - prev_beat) * 60.0 / prev_bpm
            self._segs.append((seg.beat, start_s, seg.bpm))

    def to_seconds(self, beat: float) -> float:
        b0, s0, bpm = next(s for s in reversed(self._segs) if s[0] <= beat or s is self._segs[0])
        return s0 + (beat - b0) * 60.0 / bpm

    def to_beats(self, seconds: float) -> float:
        b0, s0, bpm = next(s for s in reversed(self._segs) if s[1] <= seconds or s is self._segs[0])
        return b0 + (seconds - s0) * bpm / 60.0
```

- [ ] **Step 4:** Run `uv run pytest tests/test_timing.py -v`. Expected: 3 passed.
- [ ] **Step 5:** Commit `feat: add core map model and tempo timing` with paths `src/saber_tooth/model.py src/saber_tooth/timing.py tests/test_timing.py`.

---

### Task 3: Map IO (read v2/v3/v4, write v3 + Info v2.1) and safe filesystem

**Files:**
- Create: `src/saber_tooth/mapio/__init__.py`, `mapio/discover.py`, `mapio/read_v2.py`, `mapio/read_v3.py`, `mapio/read_v4.py`, `mapio/write.py`, `src/saber_tooth/safe_fs.py`
- Create fixtures: `tests/fixtures/maps/v2_basic/` (`info.dat`, `ExpertPlusStandard.dat`, `Hard.dat`), `tests/fixtures/maps/v3_boxes/` (`Info.dat`, `Expert.dat` with one `lightColorEventBoxGroups` entry), `tests/fixtures/maps/v4_split/` (`Info.dat` v4, `Easy.beatmap.dat`, `Lightshow.dat`), `tests/fixtures/maps/v2_bpm/` (`Info.dat`, `Expert.dat` with `_customData._BPMChanges`)
- Test: `tests/test_mapio.py`, `tests/test_safe_fs.py`

**Interfaces:**
- Consumes: Task 2 model.
- Produces:
  - `find_info(folder: Path) -> Path` (case-insensitive `info.dat`)
  - `load_map(folder: Path) -> Beatmap` (Standard set only; raises `MapParseError(str)`)
  - `write_map(beatmap: Beatmap, folder: Path, copy_from: Path | None) -> None` (writes Info v2.1 + one `<Name>.dat` v3 per difficulty; copies audio and cover from `copy_from`)
  - `LevelsWriter(root: Path)` with `.new_folder(name: str) -> Path` (returns `<root>/.<name>.partial`), `.commit(partial: Path, name: str) -> Path`, `.unique_name(base: str) -> str`, `.guard(path: Path) -> None` raising `WriteRefused` when path is inside any folder that existed when the writer was created.

Format facts (also go into `docs/map-format.md`):

| Item | v2 | v3 | v4 |
|---|---|---|---|
| note | `_time,_lineIndex,_lineLayer,_type(0 red,1 blue,3 bomb),_cutDirection` | `colorNotes[{b,x,y,c,d,a}]`, `bombNotes[{b,x,y}]` | `colorNotes[{b,i}]` + `colorNotesData[{x,y,c,d,a}]` |
| wall | `_time,_lineIndex,_type(0 full,1 crouch),_duration,_width` | `obstacles[{b,x,y,d,w,h}]` | `obstacles[{b,i}]` + `obstaclesData[{d,x,y,w,h}]` |
| event | `_events[{_time,_type,_value,_floatValue}]`, type 5 = boost | `basicBeatmapEvents[{b,et,i,f}]`, `colorBoostBeatmapEvents[{b,o}]` | lightshow file `basicEvents[{b,i}]` + `basicEventsData[{t,i,f}]` |
| bpm | `_customData._BPMChanges[{_time,_BPM}]` or `_events` type 100 | `bpmEvents[{b,m}]` | ignored in v1 (TODO entry) |

v2 crouch wall (`_type 1`) maps to `y=2,height=3`; full wall to `y=0,height=5`. Info v2: `_difficultyBeatmapSets[{_beatmapCharacteristicName:"Standard", _difficultyBeatmaps[{_difficulty,_difficultyRank,_beatmapFilename,_noteJumpMovementSpeed,_noteJumpStartBeatOffset}]}]`. Info v4: `song{title,subTitle,author}`, `audio{songFilename,bpm,previewStartTime,previewDuration}`, `coverImageFilename`, `environmentNames[]`, `colorSchemes[]`, `difficultyBeatmaps[{characteristic,difficulty,beatmapAuthors{mappers},environmentNameIdx,beatmapColorSchemeIdx,noteJumpMovementSpeed,noteJumpStartBeatOffset,beatmapDataFilename,lightshowDataFilename}]`. v4 colour scheme colours are hex strings `"RRGGBBAA"`; convert to `{r,g,b,a}` floats.

Writer output: Info `_version "2.1.0"`, `_environmentName` = `info.environment`, `_environmentNames: [info.environment]`, `_colorSchemes: [{"useOverride": true, "colorScheme": {"colorSchemeId": id, **colors}}]` when set, each difficulty `_environmentNameIdx: 0`, `_beatmapColorSchemeIdx: 0` (only when scheme set). Difficulty: `{"version":"3.3.0","bpmEvents","rotationEvents":[],"colorNotes","bombNotes","obstacles","sliders","burstSliders","waypoints":[],"basicBeatmapEvents","colorBoostBeatmapEvents","lightColorEventBoxGroups","lightRotationEventBoxGroups","lightTranslationEventBoxGroups","vfxEventBoxGroups","_fxEventsCollection":{"_fl":[],"_il":[]},"basicEventTypesWithKeywords":{"d":[]},"useNormalEventsAsCompatibleEvents":true}`; box-group and slider lists from `Difficulty.raw` (empty lists when absent). No `customData` keys at all.

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path
import pytest
from hypothesis import given, settings, strategies as st
from saber_tooth.mapio import load_map, write_map, find_info, MapParseError
from saber_tooth.model import Note, Color, Cut, Difficulty, Beatmap
from saber_tooth.timing import Timing

FIX = Path(__file__).parent / "fixtures" / "maps"

def test_discovers_mixed_case_names():
    m = load_map(FIX / "v2_basic")
    assert find_info(FIX / "v2_basic").name == "info.dat"
    assert set(m.difficulties) == {"Hard", "ExpertPlus"}

def test_v3_box_groups_preserved():
    m = load_map(FIX / "v3_boxes")
    assert len(m.difficulties["Expert"].raw["lightColorEventBoxGroups"]) == 1

def test_v4_notes_resolved():
    m = load_map(FIX / "v4_split")
    n = m.difficulties["Easy"].notes[0]
    assert (n.x, n.y, n.color) == (1, 0, Color.RED)
    assert m.difficulties["Easy"].events  # lightshow file merged

def test_v2_bpm_changes_loaded():
    d = load_map(FIX / "v2_bpm").difficulties["Expert"]
    assert d.bpm_events and d.bpm_events[0].bpm == 60.0

def test_broken_json_raises(tmp_path):
    (tmp_path / "Info.dat").write_text("{", encoding="utf-8")
    with pytest.raises(MapParseError):
        load_map(tmp_path)

def test_writer_emits_no_custom_data(tmp_path):
    m = load_map(FIX / "v2_basic")
    write_map(m, tmp_path / "out", copy_from=FIX / "v2_basic")
    text = (tmp_path / "out" / "Info.dat").read_text(encoding="utf-8")
    assert "_customData" not in text and "_requirements" not in text

notes = st.builds(Note, beat=st.integers(0, 4000).map(lambda i: i / 8), x=st.integers(0, 3), y=st.integers(0, 2),
                  color=st.sampled_from(Color), cut=st.sampled_from(Cut), angle=st.just(0))

@settings(max_examples=50)
@given(st.lists(notes, max_size=60))
def test_round_trip(tmp_path_factory, ns):
    base = load_map(FIX / "v2_basic")
    base.difficulties["Hard"].notes = sorted(ns)
    out = tmp_path_factory.mktemp("rt") / "m"
    write_map(base, out, copy_from=FIX / "v2_basic")
    assert load_map(out).difficulties["Hard"].notes == sorted(ns)
```

`tests/test_safe_fs.py`:

```python
import pytest
from saber_tooth.safe_fs import LevelsWriter, WriteRefused

def test_refuses_write_into_existing_map(tmp_path):
    (tmp_path / "abc (Song - X)").mkdir()
    w = LevelsWriter(tmp_path)
    with pytest.raises(WriteRefused):
        w.guard(tmp_path / "abc (Song - X)" / "Info.dat")

def test_commit_and_unique_name(tmp_path):
    (tmp_path / "m [saber-tooth]").mkdir()
    w = LevelsWriter(tmp_path)
    assert w.unique_name("m [saber-tooth]") == "m [saber-tooth 2]"
    p = w.new_folder("n")
    (p / "Info.dat").write_text("{}", encoding="utf-8")
    final = w.commit(p, "n")
    assert final.is_dir() and not p.exists()

def test_commit_refuses_existing(tmp_path):
    (tmp_path / "n").mkdir()
    w = LevelsWriter(tmp_path)
    p = w.new_folder("n2")
    with pytest.raises(WriteRefused):
        w.commit(p, "n")
```

- [ ] **Step 2:** Run `uv run pytest tests/test_mapio.py tests/test_safe_fs.py -v`. Expected: FAIL, import errors.
- [ ] **Step 3:** Implement. `discover.py`: `find_info` scans `folder.iterdir()` for `name.lower() == "info.dat"`; `difficulty_path(folder, filename)` resolves case-insensitively. `load_map` reads Info JSON (wrap `json.JSONDecodeError`, `KeyError`, `OSError` in `MapParseError`), dispatches on `_version` (v2) or `version` starting `"4."` (v4), then per difficulty file dispatches on `"version"` (`3.*` to `read_v3`, `4.*` to `read_v4`) else `read_v2`. Sort all lists by beat. Notes with v2 `_type 3` become `Bomb`. v2 `_events` type 100 and `_customData._BPMChanges` become `BpmEvent`. `safe_fs.LevelsWriter` snapshots `{p.resolve() for p in root.iterdir() if p.is_dir()}` at init; `guard` raises if any snapshot dir is a parent of the resolved path; `commit` uses `partial.rename(root / name)` after checking the target does not exist.
- [ ] **Step 4:** Run tests. Expected: all pass.
- [ ] **Step 5:** Commit `feat: read v2/v3/v4 maps and write v3 output safely`.

---

### Task 4 (Lane A): Difficulty profiles and swing model

**Files:**
- Create: `src/saber_tooth/profiles.py`, `src/saber_tooth/swings.py`
- Test: `tests/test_swings.py`

**Interfaces:**
- Produces: `Limits` (fields `min_hand_gap_s, max_hand_speed, reset_window_s, cross_window_s, vision_window_s`), `Profile` (fields `name, njs, offset, target_nps, grid, allow_doubles, allow_dots, error: Limits, warn: Limits, gap_beats: float`), `PROFILES: dict[str, Profile]`; `Swing(hand: Color, beat: float, seconds: float, notes: tuple[Note, ...], vector: tuple[float, float] | None, start: tuple[float, float], end: tuple[float, float])`; `build_swings(notes: list[Note], timing: Timing, window_s: float = 0.02) -> dict[Color, list[Swing]]`.

Profile table (`error` = impossible threshold for scanning, `warn` = comfort threshold that generated maps must also meet):

| name | njs | nps | grid | doubles | dots | warn gap/speed/reset/cross/vision | error gap/speed/reset/cross/vision |
|---|---|---|---|---|---|---|---|
| Easy | 10 | 1.2 | 1.0 | no | no | 0.75 / 4 / 1.5 / 0.6 / 0.5 | 0.40 / 7 / 0.8 / 0.35 / 0.30 |
| Normal | 12 | 2.0 | 0.5 | no | no | 0.50 / 5 / 1.2 / 0.5 / 0.45 | 0.30 / 10 / 0.6 / 0.30 / 0.25 |
| Hard | 14 | 3.2 | 0.5 | yes | no | 0.32 / 6.5 / 0.9 / 0.4 / 0.40 | 0.18 / 14 / 0.45 / 0.25 / 0.20 |
| Expert | 16 | 4.6 | 0.25 | yes | yes | 0.22 / 8 / 0.7 / 0.3 / 0.35 | 0.12 / 20 / 0.35 / 0.20 / 0.18 |
| ExpertPlus | 18 | 6.2 | 0.25 | yes | yes | 0.16 / 10 / 0.5 / 0.25 / 0.30 | 0.09 / 25 / 0.30 / 0.15 / 0.15 |

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

---

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
    d = Difficulty("Expert", 16, 0, notes=[Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(5.0, 1, 0, Color.RED, Cut.DOWN)],
                   bombs=[Bomb(4.5, 1, 2)])
    assert not [f for f in check_difficulty(d, T, PROFILES["Expert"]) if f.rule == "parity-break"]
```

Add analogous valid/invalid pairs for `swing-speed`, `crossover`, `vision-block`, `note-in-wall`, `missing-difficulty`, `default-environment`.

- [ ] **Step 2:** Run, expect FAIL. **Step 3:** Implement rules as pure functions `rule(d, swings, timing, profile) -> list[Finding]`, registered in `RULES: dict[str, Callable]`. **Step 4:** Run, expect pass.
- [ ] **Step 5:** Commit `feat: add playability check rules`.

---

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
    f = [f for f in check_difficulty(d, Timing(120, []), PROFILES["Expert"], busy()) if f.rule == "empty-gap"]
    assert f and f[0].beat_start == 4.0 and f[0].beat_end == 40.0

def test_gap_in_silence_is_fine():
    quiet = Analysis("x", "C major", 120.0, [i * 0.5 for i in range(120)], [], [], [], None)
    ns = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(40.0, 1, 0, Color.RED, Cut.UP)]
    d = Difficulty("Expert", 16, 0, notes=ns)
    assert not [f for f in check_difficulty(d, Timing(120, []), PROFILES["Expert"], quiet) if f.rule == "empty-gap"]
```

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add analysis reader and empty-gap rule`.

---

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

---

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

---

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
    assert folder_name('AC/DC: Back?In "Black"') == "st-acdc-backin-black (ACDC BackIn Black - saber-tooth)"
```

Plus `test_assemble_writes_five_difficulties(tmp_path)` using the Task 6 fixture with a fake `encode` that copies bytes, asserting `load_map(out)` has five difficulties, `song.egg` and `cover.png` exist, and no difficulty has findings.

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: assemble generated maps into folders`.

---

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

notes = st.builds(Note, beat=st.integers(8, 200).map(lambda i: i / 4), x=st.integers(0, 3), y=st.integers(0, 2),
                  color=st.sampled_from(Color), cut=st.sampled_from([c for c in Cut if c != Cut.ANY]))

@settings(max_examples=60, deadline=None)
@given(st.lists(notes, min_size=2, max_size=30))
def test_fix_removes_finding_and_adds_none(ns):
    m = bm(ns)
    before = {(f.rule, f.beat_start, f.beat_end) for f in run_checks(m, rules={"parity-break","wide-jump","swing-speed","stack-conflict","crossover","vision-block"})}
    for f in run_checks(m, rules={"parity-break","wide-jump","swing-speed","stack-conflict","crossover","vision-block"}):
        p = propose(m, f, None, None, 1)
        if p is None:
            continue
        after = {(g.rule, g.beat_start, g.beat_end) for g in run_checks(apply_ops(m, p.ops), rules={r for r, *_ in before} | {f.rule})}
        assert (f.rule, f.beat_start, f.beat_end) not in after
        assert after <= before
```

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add fix proposals with verified strategies`.

---

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

---

### Task 12 (Lane B): Lightshow applier

**Files:**
- Create: `lightshow/apply.py`, `lightshow/energy.py`
- Test: `tests/test_lightshow_apply.py`

**Interfaces:**
- Consumes: Task 11, Task 6 `onset_density`.
- Produces: `bar_energy(beatmap: Beatmap, timing: Timing, analysis: Analysis | None) -> list[float]`; `choose_environment(t: Templates, seed: int) -> str`; `build_lightshow(beatmap: Beatmap, timing: Timing, t: Templates, analysis: Analysis | None, seed: int, environment: str | None = None) -> ApplyLightshowPayload` where the payload is `(environment, color_scheme, events_per_difficulty)` matching Task 10's `ApplyLightshow` fields.

Atmosphere rules:
1. Energy per bar from analysis onsets, else from note density of the densest difficulty.
2. Sections: 4-bar mean energy; a change of at least 0.25 between consecutive 4-bar blocks starts a new section.
3. Each section picks one donor `source` (consistent style inside a section) with units near the section's energy; inside the section each bar takes the unit from that donor with the closest energy, cycling through a 4-bar motif so phrasing repeats.
4. Section starts with energy > 0.7 get a colour boost on; sections below 0.4 get boost off and only units with energy < 0.5.
5. Final 2 bars fade: only units with energy < 0.3, then all lights off at the last note plus 2 beats.
6. Environment: `environment` argument, else top-3 environments by unit count chosen with `random.Random(seed)`. Colour scheme: a scheme learned from a donor of that environment, else `None`.
7. All events lie within `[0, last_note_beat + 4]` and are sorted; same lightshow for every difficulty.

- [ ] **Step 1: Write failing tests**: events sorted and within song bounds; high-energy section contains a boost-on; environment is a learned one; quiet bars only use low-energy units; deterministic for equal seed.
- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: apply energy-driven vanilla lightshows`.

---

### Task 13 (Lane C): Store and job worker

**Files:**
- Create: `src/saber_tooth/store.py`, `src/saber_tooth/jobs.py`
- Test: `tests/test_store.py`, `tests/test_jobs.py`

**Interfaces:**
- Produces: `Store(path: Path)` with `upsert_map(id, folder, title, mapper, environment, parse_error)`, `list_maps() -> list[dict]`, `add_proposals(map_id, proposals: list[dict]) -> list[int]`, `proposals(map_id) -> list[dict]`, `set_status(proposal_id, status)`, `approved(map_id) -> list[dict]`, `create_job(kind) -> str`, `update_job(id, status, error=None, result=None)`, `job(id) -> dict`. Tables: `maps(id TEXT PK, folder, title, mapper, environment, parse_error, scanned_at)`, `jobs(id TEXT PK, kind, status, error, result_json, created_at, updated_at)`, `proposals(id INTEGER PK AUTOINCREMENT, map_id, rule, difficulty, severity, summary, ops_json, before_json, after_json, status, created_at)`. Status values: `pending, approved, rejected, applied`; job status `queued, running, done, failed`. `Jobs(store, max_workers=1)` with `submit(kind, fn, *args) -> job_id`; exceptions become `failed` with `str(exc)`.

- [ ] **Step 1: Write failing tests**: proposal status transitions; `set_status` on unknown id raises `KeyError`; a job whose function raises ends `failed` with the message; a job's result JSON round-trips.
- [ ] **Steps 2-4:** fail, implement (`sqlite3`, `check_same_thread=False`, one lock), pass. **Step 5:** Commit `feat: add sqlite store and job worker`.

---

### Task 14 (Lane C): beat-analyser client and audio encoding

**Files:**
- Create: `src/saber_tooth/analyser_client.py`, `src/saber_tooth/audio.py`
- Test: `tests/test_analyser_client.py`

**Interfaces:**
- Produces: `AnalyserClient(base_url: str, uploads: Path, transport: httpx.BaseTransport | None = None)` with `analyse_url(url: str) -> Analysis` and `analyse_file(path: Path, name: str) -> Analysis`; both POST without an `Origin` header, read the project name from the `Content-Disposition` filename `<name>_tracks.zip`, then `read_project(uploads / name)`. Errors raise `AnalyserError(message)` using the JSON `error` field. `encode_egg(wav: Path, egg: Path) -> None` runs `ffmpeg -y -loglevel error -i <wav> -c:a libvorbis -q:a 6 -f ogg <egg>` via `subprocess.run([...], check=True)` with a list argument (no shell).

- [ ] **Step 0:** Read `X:\Projects\beat-analyser\app\storage.py` and `app.py:103-147` to confirm how the project name is derived from an upload filename and from a YouTube URL; record the rule in `docs/architecture.md`. If the name is not recoverable from `Content-Disposition`, fall back to `GET /folders` and pick the entry whose meta `name` matches, newest first.
- [ ] **Step 1: Write failing tests** with `httpx.MockTransport`: success path returns `Analysis` read from a temp uploads dir; error JSON becomes `AnalyserError("too long")`; request has no `Origin` header.
- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add beat-analyser client and ogg encoder`.

---

### Task 15: Service layer (scan, generate, apply)

**Files:**
- Create: `src/saber_tooth/service.py`
- Test: `tests/test_service.py`

**Interfaces:**
- Consumes: Tasks 3, 5, 6, 9, 10, 12, 13, 14.
- Produces: `Service(levels: Path, data: Path, store: Store, client: AnalyserClient, encode)` with `refresh_library() -> int`, `scan(map_id) -> int` (analyses the map's audio through `client.analyse_file` for `empty-gap` and `missing-difficulty`; stores proposals; returns count), `generate(url_or_path) -> int` (stages into `data/staging/<job>`, creates one `create-map` proposal), `apply(map_id) -> Path`, `learn() -> int`. Map id: first 12 hex chars of `sha1(folder_name)`.

Apply algorithm:
1. Load original, apply all approved ops in proposal id order.
2. Run checks; if any `error` remains, or any finding exists that was not in the original scan, abort with `ApplyConflict` naming the proposal ids whose op beats overlap the new findings; nothing is written.
3. Set `_songName` suffix, write via `LevelsWriter.new_folder` then `commit(unique_name(original + " [saber-tooth]"))`, copying audio, cover and any other non-`.dat` files from the original.
4. Mark applied proposals `applied`.

- [ ] **Step 1: Write failing tests** (temp `levels` with a copy of fixture `v2_basic`, mocked client):

```python
def test_apply_twice_creates_numbered_folder(svc, levels): ...
    # approve one proposal, apply, rescan, approve, apply again
    # assert folders "<name> [saber-tooth]" and "<name> [saber-tooth 2]" exist and original bytes unchanged

def test_conflicting_proposals_abort(svc, levels): ...
    # craft two approved Move ops that put a note into the same cell as another note
    # assert ApplyConflict lists both ids and no new folder exists

def test_original_untouched(svc, levels): ...
    # hash every file in the original before and after scan+apply
```

Write each with full bodies in the test file; use a `svc` fixture building `Service` over `tmp_path`.

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add scan, generate and apply service`.

---

### Task 16: HTTP API and CLI gen-url

**Files:**
- Create: `src/saber_tooth/api.py`
- Modify: `src/saber_tooth/cli.py` (wire `gen-url`)
- Test: `tests/test_api.py`

**Interfaces:**
- Routes (spec): `GET /api/maps`, `POST /api/maps/{id}/scan` (returns `{"job": id}`), `GET /api/maps/{id}/proposals`, `POST /api/proposals/{id}/approve`, `POST /api/proposals/{id}/reject`, `POST /api/maps/{id}/approve-all`, `POST /api/maps/{id}/apply` (returns `{"job": id}`), `POST /api/generate` (JSON `{"url"}` or multipart `file`), `POST /api/lightshow/learn`, `GET /api/jobs/{id}`. Static frontend mounted at `/`. `create_app(service: Service) -> FastAPI`; module-level `app` built from env `LEVELS_DIR=/levels`, `DATA_DIR=/data`, `ANALYSER_URL=http://beat-analyser:8000`, `ANALYSER_UPLOADS=/analyser`.
- Errors: unknown map or proposal gives 404 JSON `{"error"}`; `ApplyConflict` gives job `failed` with message.

- [ ] **Step 1: Write failing tests** with `TestClient(create_app(fake_service))`: list maps, approve then reject transition, 404 on unknown id, generate with URL returns a job id.
- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: expose HTTP API`.

---

### Task 17: Frontend

**Skill:** `frontend-design:frontend-design` before writing.

**Files:**
- Create: `src/saber_tooth/web/index.html`, `web/app.js`, `web/timeline.js`, `web/style.css`
- Test: `tests/test_web.py` (served files reachable; `app.js` references only `/api/` routes that exist)

Views:
1. Library: table of maps (title, mapper, environment, errors, warnings), filter box, Scan button per row, Learn lightshows button.
2. Map detail: findings grouped by difficulty and rule; each proposal with summary, severity, Approve and Reject buttons, and a canvas timeline (`timeline.js`) showing the 4x3 grid lanes over the proposal's beat window, red and blue notes with cut arrows, before on the left and after on the right. "Approve all for this map" requires a confirm dialog. Apply button enabled when at least one proposal is approved; shows job progress and the result folder or conflict message.
3. New map: URL field and file upload, job progress, then the `create-map` proposal with per-difficulty note counts and a timeline of the first 16 bars of Expert; Approve writes the folder.

- [ ] **Steps:** test first, implement, run `uv run pytest tests/test_web.py -v`, then manual check through `task st:up` and the browser. Commit `feat: add review frontend`.

---

### Task 18: Docker, compose, final docs

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- Modify: `README.md`, `docs/architecture.md`, `docs/api.md`, `TODO.md`

`Dockerfile`: `python:3.12-slim`, `apt-get install -y --no-install-recommends ffmpeg`, copy `uv` from `ghcr.io/astral-sh/uv:0.11`, `uv sync --frozen --no-dev`, non-root user `app`, `EXPOSE 8100`, `CMD ["uv","run","--no-sync","uvicorn","saber_tooth.api:app","--host","0.0.0.0","--port","8100"]`.

`docker-compose.yml`:

```yaml
services:
  saber-tooth:
    build: .
    image: saber-tooth:latest
    ports: ["127.0.0.1:${SABER_PORT:-8100}:8100"]
    environment:
      LEVELS_DIR: /levels
      DATA_DIR: /data
      ANALYSER_URL: http://beat-analyser:8000
      ANALYSER_UPLOADS: /analyser
    volumes:
      - "${LEVELS_DIR:?set LEVELS_DIR in .env}:/levels"
      - analyser-uploads:/analyser:ro
      - saber-data:/data
    depends_on: [beat-analyser]
  beat-analyser:
    image: levialabs/beat-analyser:latest
    environment:
      MAX_UPLOAD_MB: ${MAX_UPLOAD_MB:-200}
      YT_MAX_MINUTES: ${YT_MAX_MINUTES:-20}
    volumes: ["analyser-uploads:/app/uploads"]
    read_only: true
    tmpfs: ["/tmp"]
volumes:
  analyser-uploads:
  saber-data:
```

- [ ] **Step 1:** Add task `st:compose-check` running `docker compose config -q`. Run it. Expected: exit 0.
- [ ] **Step 2:** `task st:up`, then `curl -s http://127.0.0.1:8100/api/maps` returns JSON. Run `POST /api/lightshow/learn` and confirm a non-zero unit count in the job result.
- [ ] **Step 3:** Sync docs via `crepidoma:docs-syncer`; record v1 limitations in `TODO.md` via `task todo:add` (v4 audio-data BPM, non-Standard characteristics, bombs and walls in generator).
- [ ] **Step 4:** Full gate `task ci` (or the Crepidoma gate it exposes). Commit `feat: containerise saber-tooth with beat-analyser`.
