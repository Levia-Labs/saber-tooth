import csv
import json
from dataclasses import dataclass
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


def _times(path: Path) -> list[float]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return sorted(float(row[0]) for row in csv.reader(f) if row)


def read_project(folder: Path) -> Analysis:
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    audio = folder / "audio.wav"
    return Analysis(
        name=str(meta["name"]),
        key=str(meta["key"]),
        bpm=float(meta["bpm"]),
        beats=_times(folder / "beats.csv"),
        kick=_times(folder / "kick.csv"),
        snare=_times(folder / "snare.csv"),
        hh=_times(folder / "hh.csv"),
        audio=audio if audio.is_file() else None,
    )


def onset_density(a: Analysis, start_s: float, end_s: float) -> float:
    """Weighted onsets per second in [start_s, end_s)."""
    if end_s <= start_s:
        return 0.0
    total = 0.0
    for attr, weight in WEIGHTS.items():
        total += weight * sum(1 for t in getattr(a, attr) if start_s <= t < end_s)
    return total / (end_s - start_s)
