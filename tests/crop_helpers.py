"""Synthetic maps for the crop tests. Nothing here reads or writes real user data."""

from pathlib import Path

import pytest

from saber_tooth.mapio import write_map
from saber_tooth.model import (
    DIFFICULTIES,
    BasicEvent,
    Beatmap,
    BpmEvent,
    Color,
    Cut,
    Difficulty,
    MapInfo,
    Note,
)

NAME = "Song"
DENSITY = (1, 1, 3, 3, 2, 4, 4, 1, 2)  # notes per bar, one value per 8-bar section


def info(bpm: float = 120.0) -> MapInfo:
    return MapInfo(
        "Song", "", "Artist", "Mapper", bpm, "song.ogg", "cover.jpg", 10.0, 12.0,
        "DefaultEnvironment",
    )  # fmt: skip


def diff(name: str, beats=(), bpm_events: list[BpmEvent] | tuple = ()) -> Difficulty:
    d = Difficulty(name, 16.0, 0.0)
    d.notes = [Note(float(b), i % 4, 0, Color(i % 2), Cut.ANY) for i, b in enumerate(beats)]
    d.bpm_events = list(bpm_events)
    return d


def beatmap(bpm: float = 120.0, **diffs: Difficulty) -> Beatmap:
    return Beatmap(info(bpm), dict(diffs))


def stepped_map(bars: int = 72, bpm: float = 120.0, density=DENSITY) -> Beatmap:
    """All five difficulties; `density[bar // 8 % len(density)]` notes and one light per bar."""
    out: dict[str, Difficulty] = {}
    for name in DIFFICULTIES:
        beats = [
            bar * 4.0 + k for bar in range(bars) for k in range(density[(bar // 8) % len(density)])
        ]
        d = diff(name, beats)
        d.events = [BasicEvent(bar * 4.0, 1, 5) for bar in range(bars)]
        out[name] = d
    return Beatmap(info(bpm), out)


def write_original(levels: Path, name: str = NAME, bm: Beatmap | None = None) -> Path:
    """Write a map folder with a 2-byte song and cover, like the repo fixtures."""
    folder = levels / name
    write_map(bm or stepped_map(), folder, None)
    (folder / "song.ogg").write_bytes(b"og")
    (folder / "cover.jpg").write_bytes(b"jp")
    return folder


@pytest.fixture
def cuts(monkeypatch):
    """Replace the ffmpeg cut with a fake that records its arguments and writes 3 bytes."""
    calls: list[tuple] = []

    def fake(src, dst, start_s, length_s, lead_s, fade_in_s, fade_out_s):
        calls.append((src.name, dst.name, start_s, length_s, lead_s, fade_in_s, fade_out_s))
        dst.write_bytes(b"cut")

    monkeypatch.setattr("saber_tooth.crop.write.cut_egg", fake)
    return calls
