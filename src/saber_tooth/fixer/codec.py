"""JSON-safe conversion of model objects used by fix operations."""

import copy

from saber_tooth.model import (
    BasicEvent,
    Bomb,
    BpmEvent,
    Color,
    ColorScheme,
    Cut,
    Difficulty,
    Note,
    Wall,
)

Events = tuple[list[BasicEvent], list[tuple[float, bool]], dict[str, list]]


def note_to_dict(n: Note) -> dict:
    return {
        "beat": n.beat,
        "x": n.x,
        "y": n.y,
        "color": int(n.color),
        "cut": int(n.cut),
        "angle": n.angle,
    }


def note_from_dict(d: dict) -> Note:
    return Note(
        float(d["beat"]),
        int(d["x"]),
        int(d["y"]),
        Color(d["color"]),
        Cut(d["cut"]),
        int(d.get("angle", 0)),
    )


def scheme_to_dict(s: ColorScheme | None) -> dict | None:
    return None if s is None else {"id": s.id, "colors": copy.deepcopy(s.colors)}


def scheme_from_dict(d: dict | None) -> ColorScheme | None:
    return None if d is None else ColorScheme(d["id"], copy.deepcopy(d["colors"]))


def _event_to_dict(e: BasicEvent) -> dict:
    return {"beat": e.beat, "type": e.type, "value": e.value, "float_value": e.float_value}


def _event_from_dict(d: dict) -> BasicEvent:
    return BasicEvent(float(d["beat"]), int(d["type"]), int(d["value"]), float(d["float_value"]))


def events_to_dict(ev: Events) -> dict:
    events, boosts, groups = ev
    return {
        "events": [_event_to_dict(e) for e in events],
        "boosts": [[b, on] for b, on in boosts],
        "groups": copy.deepcopy(groups),
    }


def events_from_dict(d: dict) -> Events:
    return (
        [_event_from_dict(e) for e in d["events"]],
        [(float(b), bool(on)) for b, on in d["boosts"]],
        copy.deepcopy(d["groups"]),
    )


def wall_to_dict(w: Wall) -> dict:
    return {
        "beat": w.beat,
        "x": w.x,
        "y": w.y,
        "duration": w.duration,
        "width": w.width,
        "height": w.height,
    }


def wall_from_dict(w: dict) -> Wall:
    return Wall(
        float(w["beat"]),
        int(w["x"]),
        int(w["y"]),
        float(w["duration"]),
        int(w["width"]),
        int(w["height"]),
    )


def difficulty_to_dict(d: Difficulty) -> dict:
    return {
        "name": d.name,
        "njs": d.njs,
        "offset": d.offset,
        "notes": [note_to_dict(n) for n in d.notes],
        "bombs": [{"beat": b.beat, "x": b.x, "y": b.y} for b in d.bombs],
        "walls": [wall_to_dict(w) for w in d.walls],
        "events": [_event_to_dict(e) for e in d.events],
        "boosts": [[b, on] for b, on in d.boosts],
        "bpm_events": [{"beat": e.beat, "bpm": e.bpm} for e in d.bpm_events],
        "raw": copy.deepcopy(d.raw),
        "filename": d.filename,
    }


def difficulty_from_dict(d: dict) -> Difficulty:
    return Difficulty(
        d["name"],
        float(d["njs"]),
        float(d["offset"]),
        notes=[note_from_dict(n) for n in d["notes"]],
        bombs=[Bomb(float(b["beat"]), int(b["x"]), int(b["y"])) for b in d["bombs"]],
        walls=[wall_from_dict(w) for w in d["walls"]],
        events=[_event_from_dict(e) for e in d["events"]],
        boosts=[(float(b), bool(on)) for b, on in d["boosts"]],
        bpm_events=[BpmEvent(float(e["beat"]), float(e["bpm"])) for e in d["bpm_events"]],
        raw=copy.deepcopy(d["raw"]),
        filename=d["filename"],
    )
