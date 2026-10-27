"""Fix operations: frozen, JSON-serialisable edits applied purely to a Beatmap."""

import copy
from dataclasses import dataclass, replace
from typing import ClassVar

from saber_tooth.fixer import codec
from saber_tooth.fixer.fill_op import Fill
from saber_tooth.fixer.sliders import retarget
from saber_tooth.mapio.write import BOX_KEYS, FX_KEY
from saber_tooth.model import RANKS, Beatmap, Color, ColorScheme, Cut, Difficulty, Note, Wall

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
class DeleteWall:
    KIND: ClassVar[str] = "delete-wall"
    difficulty: str
    wall: Wall

    def to_dict(self) -> dict:
        return {
            "op": self.KIND,
            "difficulty": self.difficulty,
            "wall": codec.wall_to_dict(self.wall),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DeleteWall":
        return cls(d["difficulty"], codec.wall_from_dict(d["wall"]))


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


Op = Move | Recolor | Flip | Delete | DeleteWall | Fill | AddDifficulty | ApplyLightshow
_KINDS = {
    c.KIND: c
    for c in (Move, Recolor, Flip, Delete, DeleteWall, Fill, AddDifficulty, ApplyLightshow)
}


def is_noop(op: Op) -> bool:
    """True for an op that leaves the map unchanged: a Move to the same cell and cut, a Flip to
    the same cut. A Recolor always changes the colour."""
    match op:
        case Move():
            return (op.x, op.y, op.cut) == (op.note.x, op.note.y, op.note.cut)
        case Flip():
            return op.cut == op.note.cut
    return False


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


def _fill_walls(d: Difficulty, op: Fill) -> None:
    for w in op.walls_removed:
        if w not in d.walls:
            raise OpConflict(f"fill: wall at beat {w.beat:g} not found in {d.name}")
        d.walls.remove(w)
    d.walls.extend(op.walls_added)
    d.walls.sort()


def _apply_lightshow(beatmap: Beatmap, op: ApplyLightshow) -> None:
    beatmap.info.environment = op.environment
    beatmap.info.color_scheme = op.color_scheme
    for name, (events, boosts, groups) in copy.deepcopy(op.events).items():
        if name not in beatmap.difficulties:
            continue
        _set_show(beatmap.difficulties[name], events, boosts, groups)


def _set_show(d: Difficulty, events: list, boosts: list, groups: dict) -> None:
    d.events, d.boosts = list(events), list(boosts)
    for key in (*BOX_KEYS, FX_KEY):
        d.raw.pop(key, None)
    d.raw.update(groups)


def _light_absent(beatmap: Beatmap, op: ApplyLightshow) -> None:
    """Difficulties the payload lacks (added in the same apply) get its first show."""
    if not op.events:
        return
    events, boosts, groups = copy.deepcopy(next(iter(op.events.values())))
    for name, d in beatmap.difficulties.items():
        if name not in op.events:
            _set_show(d, events, boosts, copy.deepcopy(groups))


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
            _fill_walls(d, op)
        case Move():
            d = _diff(beatmap, op.difficulty)
            _take(d, op.note, "move")
            moved = replace(op.note, x=op.x, y=op.y, cut=op.cut)
            _put(d, moved, "move")
            retarget(d, op.note, moved)
        case Flip():
            d = _diff(beatmap, op.difficulty)
            _take(d, op.note, "flip")
            flipped = replace(op.note, cut=op.cut)
            d.notes.append(flipped)
            retarget(d, op.note, flipped)
        case Recolor():
            d = _diff(beatmap, op.difficulty)
            _take(d, op.note, "recolor")
            recoloured = replace(op.note, color=Color(1 - op.note.color))
            d.notes.append(recoloured)
            retarget(d, op.note, recoloured)
        case Delete():
            d = _diff(beatmap, op.difficulty)
            _take(d, op.note, "delete")
            retarget(d, op.note, None)
        case DeleteWall():
            d = _diff(beatmap, op.difficulty)
            if op.wall not in d.walls:
                raise OpConflict(
                    f"delete-wall: wall at beat {op.wall.beat:g} not found in {d.name}"
                )
            d.walls.remove(op.wall)
    for d in beatmap.difficulties.values():
        d.notes.sort()


def apply_ops(beatmap: Beatmap, ops: list[Op]) -> Beatmap:
    """Return a deep copy of the map with every op applied in order; the input is untouched."""
    out = copy.deepcopy(beatmap)
    for op in ops:
        _apply_one(out, op)
    shows = [op for op in ops if isinstance(op, ApplyLightshow)]
    if shows:
        _light_absent(out, shows[-1])
    return out
