import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

WEIGHTS = {"kick": 1.0, "snare": 0.8, "hh": 0.3}


@dataclass(frozen=True)
class Analysis:
    name: str
    key: str
    bpm: float
    beats: list[float]
    kick: list[float]
    snare: list[float]
    hh: list[float]
    audio: Path | None
    bass: list[float] = field(default_factory=list)
    chords: list[float] = field(default_factory=list)
    melody: list[float] = field(default_factory=list)
    melody_ids: list[int] = field(default_factory=list)  # label id per melody onset


def _times(path: Path) -> list[float]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return sorted(float(row[0]) for row in csv.reader(f) if row)


def _labelled(path: Path) -> list[tuple[float, int]]:
    """(time, label id) rows sorted by time; a missing or non-numeric label reads as 0."""
    if not path.is_file():
        return []
    rows: list[tuple[float, int]] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                label = int(float(row[1])) if len(row) > 1 else 0
            except ValueError:
                label = 0
            rows.append((float(row[0]), label))
    return sorted(rows)


def read_project(folder: Path) -> Analysis:
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    audio = folder / "audio.wav"
    melody = _labelled(folder / "melody.csv")
    return Analysis(
        name=str(meta["name"]),
        key=str(meta["key"]),
        bpm=float(meta["bpm"]),
        beats=_times(folder / "beats.csv"),
        kick=_times(folder / "kick.csv"),
        snare=_times(folder / "snare.csv"),
        hh=_times(folder / "hh.csv"),
        audio=audio if audio.is_file() else None,
        bass=_times(folder / "bass.csv"),
        chords=_times(folder / "chords.csv"),
        melody=[t for t, _ in melody],
        melody_ids=[label for _, label in melody],
    )


def onset_density(a: Analysis, start_s: float, end_s: float) -> float:
    """Weighted onsets per second in [start_s, end_s)."""
    if end_s <= start_s:
        return 0.0
    total = 0.0
    for attr, weight in WEIGHTS.items():
        total += weight * sum(1 for t in getattr(a, attr) if start_s <= t < end_s)
    return total / (end_s - start_s)
