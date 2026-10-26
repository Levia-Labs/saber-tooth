"""Short human sentences describing a list of ops."""

from collections import Counter

from saber_tooth.fixer.ops import (
    AddDifficulty,
    ApplyLightshow,
    Delete,
    Fill,
    Flip,
    Move,
    Op,
    Recolor,
)
from saber_tooth.model import Color, Note


def _who(n: Note) -> str:
    return f"{Color(n.color).name.lower()} note at beat {n.beat:g}"


def describe(op: Op) -> str:
    match op:
        case Move():
            return f"Move {_who(op.note)} from ({op.note.x},{op.note.y}) to ({op.x},{op.y})"
        case Flip():
            return f"Flip {_who(op.note)} to cut {op.cut.name.lower().replace('_', ' ')}"
        case Recolor():
            other = Color(1 - op.note.color).name.lower()
            return f"Recolor {_who(op.note)} to {other}"
        case Delete():
            return f"Delete {_who(op.note)}"
        case Fill():
            span = f"{op.beat_start:g}-{op.beat_end:g}"
            return f"Fill beats {span} with {len(op.notes)} notes"
        case AddDifficulty():
            return f"Add {op.difficulty.name} difficulty with {len(op.difficulty.notes)} notes"
        case ApplyLightshow():
            return f"Apply {op.environment} lightshow to {len(op.events)} difficulties"
    raise TypeError(f"unknown op {op!r}")


def summarize(ops: list[Op]) -> str:
    if len(ops) <= 3:
        return "; ".join(describe(op) for op in ops)
    counts = Counter(type(op).__name__.lower() for op in ops)
    parts = [f"{kind} {n} notes" for kind, n in counts.items()]
    return (", ".join(parts)).capitalize()
