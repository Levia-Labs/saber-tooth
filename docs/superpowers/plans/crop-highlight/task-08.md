# Task 8: Write the cropped folder

**Files:**

- Create: `src/saber_tooth/crop/write.py`
- Modify: `tests/crop_helpers.py` (add the `cuts` fixture)
- Test: `tests/test_crop_write.py`

**Interfaces:**

Consumes: `Cropped` (`crop/shift.py`); `crop_info` (`crop/info.py`); `cut_egg`, `AudioError` (`audio.py`); `write_map(beatmap, folder, copy_from)` and `safe_name` (`mapio`); `LevelsWriter.unique_name/new_folder/commit` (`safe_fs.py`); `CropError`.

Produces (`saber_tooth.crop.write`):

```python
FADE_IN_S = 0.5

def write_cropped(levels: Path, original: Path, audio: Path, cropped: Cropped, label: str) -> Path
```

`audio` is the original song file (the service resolves it with `audio_path`; this module never imports `saber_tooth.service`, which would be a cycle). The folder is `<original.name> [<label>]`, numbered when taken, written as `.<name>.partial` then renamed, removed on any failure. The song is cut straight to `<folder>/<info.song_file>`; the cover is copied; nothing else is copied.

Tests patch `saber_tooth.crop.write.cut_egg`, so `write.py` must call it by that module-level name.

- [ ] **Step 1: Write the failing test**

In `tests/crop_helpers.py` add `import pytest` as its own import group between the stdlib group (`from pathlib import Path`) and the `saber_tooth` group, then append:

```python
@pytest.fixture
def cuts(monkeypatch):
    """Replace the ffmpeg cut with a fake that records its arguments and writes 3 bytes."""
    calls: list[tuple] = []

    def fake(src, dst, start_s, length_s, lead_s, fade_in_s, fade_out_s):
        calls.append((src.name, dst.name, start_s, length_s, lead_s, fade_in_s, fade_out_s))
        dst.write_bytes(b"cut")

    monkeypatch.setattr("saber_tooth.crop.write.cut_egg", fake)
    return calls
```

Create `tests/test_crop_write.py`:

```python
# ruff: noqa: F811
import pytest

from saber_tooth.audio import AudioError
from saber_tooth.crop.phrases import grid_timing
from saber_tooth.crop.shift import crop_beatmap
from saber_tooth.crop.write import write_cropped
from saber_tooth.mapio import load_map
from saber_tooth.model import DIFFICULTIES
from tests.crop_helpers import cuts, write_original  # noqa: F401


def _prepare(tmp_path):
    levels = tmp_path / "levels"
    levels.mkdir()
    original = write_original(levels)
    bm = load_map(original)
    return levels, original, crop_beatmap(bm, grid_timing(bm), 0.0, 128.0)


def _bytes(folder):
    return {p.name: p.read_bytes() for p in folder.iterdir()}


def test_a_new_playable_folder_is_written_and_the_original_is_untouched(tmp_path, cuts):
    levels, original, cropped = _prepare(tmp_path)
    before = _bytes(original)
    target = write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    assert target.name == "Song [1 min]"
    names = {p.name for p in target.iterdir()}
    assert names == {f"{d}.dat" for d in DIFFICULTIES} | {"Info.dat", "song.ogg", "cover.jpg"}
    assert (target / "song.ogg").read_bytes() == b"cut"
    assert (target / "cover.jpg").read_bytes() == b"jp"
    assert _bytes(original) == before
    assert [p.name for p in levels.iterdir() if p.name.endswith(".partial")] == []


def test_the_cut_gets_the_lead_in_and_the_fades(tmp_path, cuts):
    levels, original, cropped = _prepare(tmp_path)
    write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    # notes start at beat 0: a 2 s lead-in; 128 beats at 120 bpm is 64 s; the last bar is 2 s
    assert cuts == [("song.ogg", "song.ogg", 0.0, 64.0, 2.0, 0.5, 2.0)]


def test_info_has_the_suffix_and_a_preview_inside_the_new_audio(tmp_path, cuts):
    levels, original, cropped = _prepare(tmp_path)
    target = write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    back = load_map(target)
    assert back.info.song_name == "Song [1 min]"
    assert (back.info.preview_start, back.info.preview_duration) == (16.5, 10.0)  # total 66 s
    assert back.info.song_file == "song.ogg" and back.info.cover_file == "cover.jpg"


def test_a_taken_name_gets_a_number_and_never_an_overwrite(tmp_path, cuts):
    levels, original, cropped = _prepare(tmp_path)
    first = write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    second = write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    assert (first.name, second.name) == ("Song [1 min]", "Song [1 min 2]")
    assert (first / "song.ogg").read_bytes() == b"cut"


def test_an_ffmpeg_failure_leaves_no_folder(tmp_path, monkeypatch):
    levels, original, cropped = _prepare(tmp_path)

    def boom(*args):
        raise AudioError("ffmpeg failed: bad input")

    monkeypatch.setattr("saber_tooth.crop.write.cut_egg", boom)
    with pytest.raises(AudioError, match="bad input"):
        write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    assert sorted(p.name for p in levels.iterdir()) == ["Song"]
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_crop_write.py -q`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'saber_tooth.crop.write'`.

- [ ] **Step 3: Implement**

Create `src/saber_tooth/crop/write.py`:

```python
"""Write a cropped map into a new folder beside the original, never into an existing one."""

import shutil
from dataclasses import replace
from pathlib import Path

from saber_tooth.audio import cut_egg
from saber_tooth.crop.info import crop_info
from saber_tooth.crop.shift import Cropped
from saber_tooth.mapio import write_map
from saber_tooth.mapio.errors import safe_name
from saber_tooth.safe_fs import LevelsWriter

FADE_IN_S = 0.5


def _copy_cover(original: Path, partial: Path, name: str) -> None:
    if not name:
        return
    safe_name(name)
    src = (original / name).resolve()
    if original.resolve() in src.parents and src.is_file():
        shutil.copyfile(src, partial / name)


def write_cropped(levels: Path, original: Path, audio: Path, cropped: Cropped, label: str) -> Path:
    """Write `<original> [label]` (numbered when taken): Info and difficulty files, the cover and
    the cut song. The partial folder is removed on any failure."""
    info = cropped.beatmap.info
    beatmap = replace(
        cropped.beatmap, info=crop_info(info, cropped.lead_s + cropped.length_s, label)
    )
    writer = LevelsWriter(levels)
    name = writer.unique_name(f"{original.name} [{label}]")
    partial = writer.new_folder(name)
    try:
        write_map(beatmap, partial, None)
        _copy_cover(original, partial, info.cover_file)
        cut_egg(
            audio,
            partial / safe_name(info.song_file),
            cropped.start_s,
            cropped.length_s,
            cropped.lead_s,
            FADE_IN_S,
            cropped.fade_out_s,
        )
        return writer.commit(partial, name)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_crop_write.py -q`
Expected: 5 passed.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/crop/write.py tests/crop_helpers.py tests/test_crop_write.py && uv run ruff format --check src/saber_tooth/crop/write.py tests/crop_helpers.py tests/test_crop_write.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: write cropped maps through the safe folder writer"` (subagents never commit).
