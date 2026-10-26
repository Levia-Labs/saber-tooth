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

| Item  | v2                                                                     | v3                                                                 | v4                                                               |
| ----- | ---------------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------- |
| note  | `_time,_lineIndex,_lineLayer,_type(0 red,1 blue,3 bomb),_cutDirection` | `colorNotes[{b,x,y,c,d,a}]`, `bombNotes[{b,x,y}]`                  | `colorNotes[{b,i}]` + `colorNotesData[{x,y,c,d,a}]`              |
| wall  | `_time,_lineIndex,_type(0 full,1 crouch),_duration,_width`             | `obstacles[{b,x,y,d,w,h}]`                                         | `obstacles[{b,i}]` + `obstaclesData[{d,x,y,w,h}]`                |
| event | `_events[{_time,_type,_value,_floatValue}]`, type 5 = boost            | `basicBeatmapEvents[{b,et,i,f}]`, `colorBoostBeatmapEvents[{b,o}]` | lightshow file `basicEvents[{b,i}]` + `basicEventsData[{t,i,f}]` |
| bpm   | `_customData._BPMChanges[{_time,_BPM}]` or `_events` type 100          | `bpmEvents[{b,m}]`                                                 | ignored in v1 (TODO entry)                                       |

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


notes = st.builds(
    Note,
    beat=st.integers(0, 4000).map(lambda i: i / 8),
    x=st.integers(0, 3),
    y=st.integers(0, 2),
    color=st.sampled_from(Color),
    cut=st.sampled_from(Cut),
    angle=st.just(0),
)


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
