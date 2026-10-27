"""The fill operation: notes and wall changes that close an empty gap."""

from dataclasses import dataclass
from typing import ClassVar

from saber_tooth.fixer import codec
from saber_tooth.model import Note, Wall


@dataclass(frozen=True)
class Fill:
    KIND: ClassVar[str] = "fill"
    difficulty: str
    beat_start: float
    beat_end: float
    notes: tuple[Note, ...]
    walls_added: tuple[Wall, ...] = ()
    walls_removed: tuple[Wall, ...] = ()

    def to_dict(self) -> dict:
        return {
            "op": self.KIND,
            "difficulty": self.difficulty,
            "beat_start": self.beat_start,
            "beat_end": self.beat_end,
            "notes": [codec.note_to_dict(n) for n in self.notes],
            "walls_added": [codec.wall_to_dict(w) for w in self.walls_added],
            "walls_removed": [codec.wall_to_dict(w) for w in self.walls_removed],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Fill":
        notes = tuple(codec.note_from_dict(n) for n in d["notes"])
        added = tuple(codec.wall_from_dict(w) for w in d.get("walls_added", []))
        removed = tuple(codec.wall_from_dict(w) for w in d.get("walls_removed", []))
        return cls(
            d["difficulty"], float(d["beat_start"]), float(d["beat_end"]), notes, added, removed
        )
