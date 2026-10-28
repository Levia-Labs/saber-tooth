# Task 10: Service functions and the crop job body

`Service` is built in `service/core.py` (300 lines, edited by another lane), so the three methods live in `service/crop.py` and are attached the way `fix_map` is (`service/__init__.py:6`).

**Files:**

- Create: `src/saber_tooth/service/crop.py`
- Modify: `src/saber_tooth/service/__init__.py`
- Modify: `tests/crop_helpers.py` (add `make_service`)
- Test: `tests/test_crop_service.py`

**Interfaces:**

Consumes: `build_timeline`, `resolve_window`, `timeline_dict`, `Timeline` (`crop/timeline.py`); `crop_beatmap` (`crop/shift.py`); `write_cropped` (`crop/write.py`); `hardest` (`crop/phrases.py`); `CropError`; `Service._folder(map_id) -> Path`, `Service._load(folder) -> Beatmap`, `Service.levels`, `Service.uploads`, `Service.store.scan_info(map_id)`, `Service.refresh_library()`, `_lock`; `folder_duration(folder, beatmap)` and `audio_path(folder, name)` (`service/duration.py`); `stored_analysis(uploads, info)` (`service/verify.py`); `map_id_for(folder_name)` (`service/util.py`).

Produces (`saber_tooth.service.crop`, attached to `Service`):

```python
LABELS = {60: "1 min", 120: "2 min"}

def crop_timeline(svc, map_id: str) -> dict                       # Service.crop_timeline(map_id)
def crop_check(svc, map_id: str, start_beat: float, end_beat: float) -> None   # Service.crop_check(...); raises InvalidWindow
def crop_map(svc, map_id: str, start_beat: float, end_beat: float) -> dict     # Service.crop_map(...); the job body
```

`crop_map` returns `{"map_id", "folder", "cropped_id", "label", "start_beat", "end_beat", "length_s"}`. The timeline uses the analysis already stored by a scan (`stored_analysis`); it never calls the analyser, which is slow. A map that was never scanned is `map_only`.

Produces (`tests/crop_helpers.py`): `make_service(tmp_path, bm=None) -> Service` (levels folder with one synthetic map named `Song`, store, fake analyser client, `refresh_library()` already run).

- [ ] **Step 1: Write the failing test**

Append to `tests/crop_helpers.py` (add these imports to the existing import groups: `from saber_tooth.service import Service`, `from saber_tooth.store import Store`, `from tests.test_service import _client, _fake_encode`):

```python
def make_service(tmp_path: Path, bm: Beatmap | None = None) -> Service:
    levels = tmp_path / "levels"
    levels.mkdir()
    write_original(levels, NAME, bm)
    data = tmp_path / "data"
    data.mkdir()
    svc = Service(levels, data, Store(data / "s.db"), _client(tmp_path), _fake_encode)
    svc.refresh_library()
    return svc
```

Create `tests/test_crop_service.py`:

```python
# ruff: noqa: F811
import json

import pytest

from saber_tooth.crop.errors import CropError, InvalidWindow, NoNotes
from saber_tooth.mapio import load_map
from saber_tooth.service import map_id_for
from tests.crop_helpers import NAME, cuts, make_service  # noqa: F401
from tests.test_service import _hashes

MID = map_id_for(NAME)


def test_timeline_of_an_unscanned_map_is_map_only(tmp_path):
    svc = make_service(tmp_path)
    tl = svc.crop_timeline(MID)
    assert tl["map_id"] == MID and tl["map_only"] is True and tl["grid_drift_s"] is None
    assert set(tl["lengths"]) == {"60", "120"} and tl["hardest"] == "ExpertPlus"
    assert tl["lengths"]["60"]["enabled"] and tl["lengths"]["120"]["enabled"]
    json.dumps(tl)


def test_a_scanned_map_uses_its_stored_analysis(tmp_path):
    svc = make_service(tmp_path)
    project = svc.uploads / "proj"
    project.mkdir(parents=True)
    (project / "meta.json").write_text(
        json.dumps({"name": "proj", "key": "C", "bpm": 120}), encoding="utf-8"
    )
    grid = "".join(f"{i * 0.5},1\n" for i in range(300))
    (project / "beats.csv").write_text(grid, encoding="utf-8")
    (project / "kick.csv").write_text(grid, encoding="utf-8")
    svc.store.replace_open_proposals(MID, [], {"findings": [], "analysis": "proj"})
    tl = svc.crop_timeline(MID)
    assert tl["map_only"] is False
    assert tl["grid_drift_s"] == pytest.approx(0.0)


def test_crop_map_writes_a_folder_and_leaves_the_original(tmp_path, cuts):
    svc = make_service(tmp_path)
    original = svc.levels / NAME
    before = _hashes(original)
    window = svc.crop_timeline(MID)["lengths"]["60"]["suggestions"][0]
    result = svc.crop_map(MID, window["start_beat"], window["end_beat"])
    assert result["folder"] == "Song [1 min]" and result["label"] == "1 min"
    assert result["cropped_id"] == map_id_for("Song [1 min]")
    assert result["length_s"] == pytest.approx(window["length_s"])
    assert _hashes(original) == before
    written = load_map(svc.levels / result["folder"])
    assert len(written.difficulties) == 5 and len(cuts) == 1
    assert any(m["folder"] == "Song [1 min]" for m in svc.store.list_maps())


def test_a_two_minute_window_is_labelled_two_minutes(tmp_path, cuts):
    svc = make_service(tmp_path)
    window = svc.crop_timeline(MID)["lengths"]["120"]["suggestions"][0]
    assert svc.crop_map(MID, window["start_beat"], window["end_beat"])["label"] == "2 min"


def test_crop_check_names_the_broken_rule(tmp_path):
    svc = make_service(tmp_path)
    with pytest.raises(InvalidWindow, match="section boundary"):
        svc.crop_check(MID, 5.0, 133.0)
    window = svc.crop_timeline(MID)["lengths"]["60"]["suggestions"][0]
    svc.crop_check(MID, window["start_beat"], window["end_beat"])


def test_a_missing_song_file_fails_the_crop_without_a_folder(tmp_path, cuts):
    svc = make_service(tmp_path)
    window = svc.crop_timeline(MID)["lengths"]["60"]["suggestions"][0]
    (svc.levels / NAME / "song.ogg").unlink()
    with pytest.raises(CropError, match="song file"):
        svc.crop_map(MID, window["start_beat"], window["end_beat"])
    assert sorted(p.name for p in svc.levels.iterdir()) == [NAME]


def test_map_without_standard_notes_is_refused(tmp_path):
    svc = make_service(tmp_path)
    info = svc.levels / NAME / "Info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace('"Standard"', '"360Degree"'), encoding="utf-8"
    )
    with pytest.raises(NoNotes, match="no Standard difficulty has notes"):
        svc.crop_timeline(MID)
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_crop_service.py -q`
Expected: FAIL: `AttributeError: 'Service' object has no attribute 'crop_timeline'`.

- [ ] **Step 3: Implement**

Create `src/saber_tooth/service/crop.py`:

```python
"""Service side of the crop highlight: the timeline, the window check and the crop job."""

import logging
from pathlib import Path

from saber_tooth.crop.errors import CropError
from saber_tooth.crop.phrases import hardest
from saber_tooth.crop.shift import crop_beatmap
from saber_tooth.crop.timeline import Timeline, build_timeline, resolve_window, timeline_dict
from saber_tooth.crop.write import write_cropped
from saber_tooth.model import Beatmap
from saber_tooth.service.duration import audio_path, folder_duration
from saber_tooth.service.util import map_id_for
from saber_tooth.service.verify import stored_analysis

log = logging.getLogger(__name__)

LABELS = {60: "1 min", 120: "2 min"}


def _timeline(svc, map_id: str) -> tuple[Path, Beatmap, Timeline]:
    folder = svc._folder(map_id)
    beatmap = svc._load(folder)
    hardest(beatmap)  # NoNotes first: a map with no Standard notes has no length either
    duration = folder_duration(folder, beatmap)
    if duration is None:
        raise CropError("the song length is unknown")
    analysis = stored_analysis(svc.uploads, svc.store.scan_info(map_id))
    return folder, beatmap, build_timeline(beatmap, duration, analysis)


def crop_timeline(svc, map_id: str) -> dict:
    """NPS per difficulty, sections and the 1 and 2 minute plans for one map."""
    return timeline_dict(_timeline(svc, map_id)[2], map_id)


def crop_check(svc, map_id: str, start_beat: float, end_beat: float) -> None:
    """Raise InvalidWindow when the pair breaks a window rule; used before a job is queued."""
    resolve_window(_timeline(svc, map_id)[2], start_beat, end_beat)


def crop_map(svc, map_id: str, start_beat: float, end_beat: float) -> dict:
    """Crop a map into a new `<map> [1 min]` or `[2 min]` folder; the original is never changed."""
    folder, beatmap, tl = _timeline(svc, map_id)
    plan, start, end = resolve_window(tl, start_beat, end_beat)
    audio = audio_path(folder, beatmap.info.song_file)
    if audio is None:
        raise CropError("the map has no readable song file")
    label = LABELS[plan.target_s]
    cropped = crop_beatmap(beatmap, tl.timing, start.beat, end.beat)
    target = write_cropped(svc.levels, folder, audio, cropped, label)
    try:
        svc.refresh_library()
    except Exception:
        log.exception("library refresh failed after cropping %s", map_id)
    return {
        "map_id": map_id,
        "folder": target.name,
        "cropped_id": map_id_for(target.name),
        "label": label,
        "start_beat": start.beat,
        "end_beat": end.beat,
        "length_s": end.seconds - start.seconds,
    }
```

Edit `src/saber_tooth/service/__init__.py`: add `from saber_tooth.service.crop import crop_check, crop_map, crop_timeline` after the `fix_map` import line, and after the `Service.fix_map = ...` line add:

```python
Service.crop_timeline = crop_timeline  # type: ignore[attr-defined]  # crop highlight, see crop.py
Service.crop_check = crop_check  # type: ignore[attr-defined]
Service.crop_map = crop_map  # type: ignore[attr-defined]
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_crop_service.py tests/test_fix_map.py -q`
Expected: 7 passed in `test_crop_service.py`; `test_fix_map.py` still passes.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/service tests/crop_helpers.py tests/test_crop_service.py && uv run ruff format --check src/saber_tooth/service/crop.py tests/crop_helpers.py tests/test_crop_service.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: service crop timeline and crop job"` (subagents never commit).

---
