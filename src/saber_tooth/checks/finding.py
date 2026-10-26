from dataclasses import asdict, dataclass
from typing import Literal

from saber_tooth.model import Note, Wall

Severity = Literal["error", "warn"]


@dataclass(frozen=True)
class Finding:
    rule: str
    difficulty: str
    beat_start: float
    beat_end: float
    severity: Severity
    message: str
    notes: tuple[Note, ...] = ()
    walls: tuple[Wall, ...] = ()

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "difficulty": self.difficulty,
            "beat_start": self.beat_start,
            "beat_end": self.beat_end,
            "severity": self.severity,
            "message": self.message,
            "notes": [
                {
                    "beat": n.beat,
                    "x": n.x,
                    "y": n.y,
                    "color": int(n.color),
                    "cut": int(n.cut),
                    "angle": n.angle,
                }
                for n in self.notes
            ],
            "walls": [asdict(w) for w in self.walls],
        }

    def sort_key(self) -> tuple:
        return (self.difficulty, self.beat_start, self.rule, self.beat_end, self.message)


def grade_below(value: float, error: float, warn: float) -> Severity | None:
    """Severity for a value that is bad when smaller than the limit."""
    if value < error:
        return "error"
    if value < warn:
        return "warn"
    return None


def grade_above(value: float, error: float, warn: float) -> Severity | None:
    """Severity for a value that is bad when larger than the limit."""
    if value > error:
        return "error"
    if value > warn:
        return "warn"
    return None
