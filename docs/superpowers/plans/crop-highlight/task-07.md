# Task 7: ffmpeg cut and Info.dat fields

**Files:**

- Modify: `src/saber_tooth/audio.py`
- Create: `src/saber_tooth/crop/info.py`
- Test: `tests/test_audio_cut.py`
- Test: `tests/test_crop_info.py`

**Interfaces:**

Consumes: `subprocess` use and `AudioError` in `audio.py`; `MapInfo`.

Produces:

```python
# saber_tooth.audio
def cut_egg(src: Path, dst: Path, start_s: float, length_s: float, lead_s: float,
            fade_in_s: float, fade_out_s: float) -> None
    # cut length_s from start_s, put lead_s of silence first, fade in at the music start, fade out over the last fade_out_s; Ogg Vorbis at dst

# saber_tooth.crop.info
PREVIEW_S = 10.0
PREVIEW_AT = 0.25
def crop_info(info: MapInfo, total_s: float, label: str) -> MapInfo
    # song_name + " [label]"; preview_duration <= 10 s and <= total_s; preview_start inside [0, total_s - duration]
```

Info.dat v2.1.0 (`mapio/write.py:82-101`) has no duration field; the cut file's own Ogg length is what `service/duration.py:46-60` reads, so no duration is written.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_audio_cut.py`:

```python
import subprocess
from pathlib import Path

import pytest

from saber_tooth import audio


def test_cut_egg_argv_with_a_lead_in(monkeypatch):
    calls = []
    monkeypatch.setattr(audio.subprocess, "run", lambda *a, **k: calls.append((a, k)))
    audio.cut_egg(Path("a.ogg"), Path("b.ogg"), 32.0, 64.0, 1.5, 0.5, 2.0)
    assert calls[0][0][0] == [
        "ffmpeg", "-y", "-loglevel", "error", "-ss", "32.000", "-t", "64.000", "-i", "a.ogg",
        "-af",
        "adelay=1500:all=1,afade=t=in:st=1.500:d=0.500,afade=t=out:st=63.500:d=2.000",
        "-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", "b.ogg",
    ]  # fmt: skip
    assert calls[0][1]["check"] is True and not calls[0][1].get("shell")


def test_cut_egg_argv_without_a_lead_in(monkeypatch):
    calls = []
    monkeypatch.setattr(audio.subprocess, "run", lambda *a, **k: calls.append((a, k)))
    audio.cut_egg(Path("a.ogg"), Path("b.ogg"), 0.0, 64.0, 0.0, 0.5, 2.0)
    argv = calls[0][0][0]
    assert (
        argv[argv.index("-af") + 1] == "afade=t=in:st=0.000:d=0.500,afade=t=out:st=62.000:d=2.000"
    )


def test_cut_egg_reports_a_missing_ffmpeg(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(audio.subprocess, "run", boom)
    with pytest.raises(audio.AudioError, match="not installed"):
        audio.cut_egg(Path("a.ogg"), Path("b.ogg"), 0.0, 60.0, 0.0, 0.5, 2.0)


def test_cut_egg_reports_an_ffmpeg_failure(monkeypatch):
    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, "ffmpeg", stderr=b"bad input")

    monkeypatch.setattr(audio.subprocess, "run", boom)
    with pytest.raises(audio.AudioError, match="bad input"):
        audio.cut_egg(Path("a.ogg"), Path("b.ogg"), 0.0, 60.0, 0.0, 0.5, 2.0)
```

Create `tests/test_crop_info.py`:

```python
from saber_tooth.crop.info import crop_info
from tests.crop_helpers import info


def test_song_name_gets_the_label_and_the_preview_lies_inside_the_audio():
    out = crop_info(info(), 66.0, "1 min")
    assert out.song_name == "Song [1 min]"
    assert (out.preview_start, out.preview_duration) == (16.5, 10.0)  # a quarter in, 10 s long


def test_a_short_clip_gets_a_short_preview_from_the_start():
    out = crop_info(info(), 8.0, "1 min")
    assert (out.preview_start, out.preview_duration) == (0.0, 8.0)


def test_a_missing_preview_length_defaults_to_ten_seconds():
    base = info()
    base.preview_duration = 0.0
    assert crop_info(base, 60.0, "2 min").preview_duration == 10.0


def test_the_original_info_is_not_mutated():
    base = info()
    crop_info(base, 66.0, "1 min")
    assert base.song_name == "Song" and base.preview_start == 10.0
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_audio_cut.py tests/test_crop_info.py -q`
Expected: FAIL: `AttributeError: module 'saber_tooth.audio' has no attribute 'cut_egg'` and `ModuleNotFoundError: No module named 'saber_tooth.crop.info'`.

- [ ] **Step 3: Implement**

Replace the body of `src/saber_tooth/audio.py` after the `AudioError` class with:

```python
def _run(argv: list[str]) -> None:
    try:
        subprocess.run(argv, check=True, capture_output=True)  # nosec B603 - list argv, no shell
    except FileNotFoundError as exc:
        raise AudioError("ffmpeg is not installed") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
        raise AudioError(f"ffmpeg failed: {detail}") from exc


def encode_egg(wav: Path, egg: Path) -> None:
    """Encode `wav` to Ogg Vorbis at `egg` (Beat Saber's .egg container)."""
    argv = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
        "-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", str(egg),
    ]  # fmt: skip
    _run(argv)


def cut_egg(
    src: Path,
    dst: Path,
    start_s: float,
    length_s: float,
    lead_s: float,
    fade_in_s: float,
    fade_out_s: float,
) -> None:
    """Cut `length_s` seconds from `start_s`, put `lead_s` of silence before them, fade in at the
    music start and out over the last `fade_out_s`; Ogg Vorbis at `dst`."""
    filters = []
    if lead_s > 0:
        filters.append(f"adelay={round(lead_s * 1000)}:all=1")
    filters.append(f"afade=t=in:st={lead_s:.3f}:d={fade_in_s:.3f}")
    filters.append(f"afade=t=out:st={lead_s + length_s - fade_out_s:.3f}:d={fade_out_s:.3f}")
    argv = [
        "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start_s:.3f}", "-t", f"{length_s:.3f}",
        "-i", str(src), "-af", ",".join(filters),
        "-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", str(dst),
    ]  # fmt: skip
    _run(argv)
```

Create `src/saber_tooth/crop/info.py`:

```python
"""Info.dat fields of a cropped map."""

from dataclasses import replace

from saber_tooth.model import MapInfo

PREVIEW_S = 10.0
PREVIEW_AT = 0.25  # the preview starts a quarter of the way in


def crop_info(info: MapInfo, total_s: float, label: str) -> MapInfo:
    """Song name suffix and a preview that lies inside the new audio of `total_s` seconds."""
    duration = min(info.preview_duration or PREVIEW_S, PREVIEW_S, total_s)
    start = max(0.0, min(total_s * PREVIEW_AT, total_s - duration))
    return replace(
        info,
        song_name=f"{info.song_name} [{label}]",
        preview_start=round(start, 1),
        preview_duration=round(duration, 1),
    )
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_audio_cut.py tests/test_crop_info.py tests/test_audio.py -q`
Expected: all pass; `tests/test_audio.py` proves `encode_egg` is unchanged.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/audio.py src/saber_tooth/crop/info.py tests/test_audio_cut.py tests/test_crop_info.py && uv run ruff format --check src/saber_tooth/audio.py src/saber_tooth/crop/info.py tests/test_audio_cut.py tests/test_crop_info.py`
Expected: no findings.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: ffmpeg cut with fades and cropped Info fields"` (subagents never commit).

---
