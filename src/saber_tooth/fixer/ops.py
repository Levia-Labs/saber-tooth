"""Fix operations: frozen, JSON-serialisable edits applied purely to a Beatmap."""

import copy
from dataclasses import dataclass, replace
from typing import ClassVar

from saber_tooth.fixer import codec
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import RANKS, Beatmap, Color, ColorScheme, Cut, Difficulty, Note

EPS = 1e-6


class OpConflict(ValueError):
    """An operation no longer matches the map it is applied to."""


def _note_op(kind: str, difficulty: str, note: Note, **extra) -> dict:
    return {"op": kind, "difficulty": difficulty, "note": codec.note_to_dict(note), **extra}


@dataclass(frozen=True)
class Move:
    KIND: ClassVar[str] = "move"
    difficulty: str
    note: Note
    x: int
    y: int
    cut: Cut

    def to_dict(self) -> dict:
        return _note_op(
            self.KIND, self.difficulty, self.note, x=self.x, y=self.y, cut=int(self.cut)
        )

    @classmethod
    def from_dict(cls, d: dict) -> "Move":
        note = codec.note_from_dict(d["note"])
        return cls(d["difficulty"], note, int(d["x"]), int(d["y"]), Cut(d["cut"]))


@dataclass(frozen=True)
class Recolor:
    KIND: ClassVar[str] = "recolor"
    difficulty: str
    note: Note

    def to_dict(self) -> dict:
        return _note_op(self.KIND, self.difficulty, self.note)

    @classmethod
    def from_dict(cls, d: dict) -> "Recolor":
        return cls(d["difficulty"], codec.note_from_dict(d["note"]))


@dataclass(frozen=True)
class Flip:
    KIND: ClassVar[str] = "flip"
    difficulty: str
    note: Note
    cut: Cut

    def to_dict(self) -> dict:
        return _note_op(self.KIND, self.difficulty, self.note, cut=int(self.cut))

    @classmethod
    def from_dict(cls, d: dict) -> "Flip":
        return cls(d["difficulty"], codec.note_from_dict(d["note"]), Cut(d["cut"]))


@dataclass(frozen=True)
class Delete:
    KIND: ClassVar[str] = "delete"
    difficulty: str
    note: Note

    def to_dict(self) -> dict:
        return _note_op(self.KIND, self.difficulty, self.note)

    @classmethod
    def from_dict(cls, d: dict) -> "Delete":
        return cls(d["difficulty"], codec.note_from_dict(d["note"]))


@dataclass(frozen=True)
class Fill:
    KIND: ClassVar[str] = "fill"
    difficulty: str
    beat_start: float
    beat_end: float
    notes: tuple[Note, ...]

    def to_dict(self) -> dict:
        return {
            "op": self.KIND,
            "difficulty": self.difficulty,
            "beat_start": self.beat_start,
            "beat_end": self.beat_end,
            "notes": [codec.note_to_dict(n) for n in self.notes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Fill":
        notes = tuple(codec.note_from_dict(n) for n in d["notes"])
        return cls(d["difficulty"], float(d["beat_start"]), float(d["beat_end"]), notes)


@dataclass(frozen=True)
class AddDifficulty:
    KIND: ClassVar[str] = "add-difficulty"
    difficulty: Difficulty

    def to_dict(self) -> dict:
        return {"op": self.KIND, "difficulty": codec.difficulty_to_dict(self.difficulty)}

    @classmethod
    def from_dict(cls, d: dict) -> "AddDifficulty":
        return cls(codec.difficulty_from_dict(d["difficulty"]))


@dataclass(frozen=True)
class ApplyLightshow:
    KIND: ClassVar[str] = "apply-lightshow"
    environment: str
    color_scheme: ColorScheme | None
    events: dict[str, codec.Events]

    @classmethod
    def from_payload(cls, payload) -> "ApplyLightshow":
        events = copy.deepcopy(dict(payload.events))
        return cls(payload.environment, payload.color_scheme, events)

    def to_dict(self) -> dict:
        return {
            "op": self.KIND,
            "environment": self.environment,
            "color_scheme": codec.scheme_to_dict(self.color_scheme),
            "events": {name: codec.events_to_dict(ev) for name, ev in self.events.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ApplyLightshow":
        events = {name: codec.events_from_dict(ev) for name, ev in d["events"].items()}
        return cls(d["environment"], codec.scheme_from_dict(d["color_scheme"]), events)


Op = Move | Recolor | Flip | Delete | Fill | AddDifficulty | ApplyLightshow
_KINDS = {c.KIND: c for c in (Move, Recolor, Flip, Delete, Fill, AddDifficulty, ApplyLightshow)}


def op_from_dict(d: dict) -> Op:
    try:
        return _KINDS[d["op"]].from_dict(d)
    except KeyError as e:
        raise ValueError(f"unknown or malformed operation: {e}") from e


def _diff(beatmap: Beatmap, name: str) -> Difficulty:
    if name not in beatmap.difficulties:
        raise OpConflict(f"difficulty {name} does not exist")
    return beatmap.difficulties[name]


def _take(d: Difficulty, note: Note, what: str) -> None:
    try:
        d.notes.remove(note)
    except ValueError:
        raise OpConflict(f"{what}: note at beat {note.beat:g} not found in {d.name}") from None


def _put(d: Difficulty, note: Note, what: str) -> None:
    if any(abs(n.beat - note.beat) < EPS and (n.x, n.y) == (note.x, note.y) for n in d.notes):
        raise OpConflict(f"{what}: cell ({note.x},{note.y}) at beat {note.beat:g} is taken")
    d.notes.append(note)


def _apply_lightshow(beatmap: Beatmap, op: ApplyLightshow) -> None:
    beatmap.info.environment = op.environment
    beatmap.info.color_scheme = op.color_scheme
    for name, (events, boosts, groups) in copy.deepcopy(op.events).items():
        if name not in beatmap.difficulties:
            continue
        d = beatmap.difficulties[name]
        d.events, d.boosts = list(events), list(boosts)
        for key in BOX_KEYS:
            d.raw.pop(key, None)
        d.raw.update(groups)


def _add_difficulty(beatmap: Beatmap, op: AddDifficulty) -> None:
    name = op.difficulty.name
    if name in beatmap.difficulties:
        raise OpConflict(f"difficulty {name} already exists")
    beatmap.difficulties[name] = copy.deepcopy(op.difficulty)
    ordered = sorted(beatmap.difficulties.items(), key=lambda kv: RANKS.get(kv[0], 99))
    beatmap.difficulties = dict(ordered)


def _apply_one(beatmap: Beatmap, op: Op) -> None:
    match op:
        case ApplyLightshow():
            _apply_lightshow(beatmap, op)
        case AddDifficulty():
            _add_difficulty(beatmap, op)
        case Fill():
            d = _diff(beatmap, op.difficulty)
            for n in op.notes:
                if not op.beat_start - EPS <= n.beat <= op.beat_end + EPS:
                    raise OpConflict(f"fill: note at beat {n.beat:g} is outside the range")
                _put(d, n, "fill")
        case Move():
            d = _diff(beatmap, op.difficulty)
            _take(d, op.note, "move")
            _put(d, replace(op.note, x=op.x, y=op.y, cut=op.cut), "move")
        case Flip():
            d = _diff(beatmap, op.difficulty)
            _take(d, op.note, "flip")
            d.notes.append(replace(op.note, cut=op.cut))
        case Recolor():
            d = _diff(beatmap, op.difficulty)
            _take(d, op.note, "recolor")
            d.notes.append(replace(op.note, color=Color(1 - op.note.color)))
        case Delete():
            _take(_diff(beatmap, op.difficulty), op.note, "delete")
    for d in beatmap.difficulties.values():
        d.notes.sort()


def apply_ops(beatmap: Beatmap, ops: list[Op]) -> Beatmap:
    """Return a deep copy of the map with every op applied in order; the input is untouched."""
    out = copy.deepcopy(beatmap)
    for op in ops:
        _apply_one(out, op)
    return out
