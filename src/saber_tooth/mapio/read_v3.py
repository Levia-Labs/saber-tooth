from saber_tooth.mapio.errors import MapParseError
from saber_tooth.mapio.read_v2 import _sort
from saber_tooth.model import BasicEvent, Bomb, BpmEvent, Color, Cut, Difficulty, Note, Wall

RAW_KEYS = (
    "lightColorEventBoxGroups",
    "lightRotationEventBoxGroups",
    "lightTranslationEventBoxGroups",
    "vfxEventBoxGroups",
    "sliders",
    "burstSliders",
)


def read_v3(data: dict, name: str, njs: float, offset: float, filename: str) -> Difficulty:
    d = Difficulty(name=name, njs=njs, offset=offset, filename=filename)
    try:
        d.notes = [
            Note(
                float(n["b"]),
                int(n["x"]),
                int(n["y"]),
                Color(int(n["c"])),
                Cut(int(n["d"]) % 9),
                int(n.get("a", 0)),
            )
            for n in data.get("colorNotes", [])
        ]
        d.bombs = [Bomb(float(b["b"]), int(b["x"]), int(b["y"])) for b in data.get("bombNotes", [])]
        d.walls = [
            Wall(float(w["b"]), int(w["x"]), int(w["y"]), float(w["d"]), int(w["w"]), int(w["h"]))
            for w in data.get("obstacles", [])
        ]
        d.events = [
            BasicEvent(float(e["b"]), int(e["et"]), int(e["i"]), float(e.get("f", 1.0)))
            for e in data.get("basicBeatmapEvents", [])
        ]
        d.boosts = [(float(e["b"]), bool(e["o"])) for e in data.get("colorBoostBeatmapEvents", [])]
        d.bpm_events = [BpmEvent(float(e["b"]), float(e["m"])) for e in data.get("bpmEvents", [])]
    except (KeyError, TypeError, ValueError) as exc:
        raise MapParseError(f"bad v3 difficulty {filename}: {exc!r}") from exc
    d.raw = {k: list(data.get(k) or []) for k in RAW_KEYS}
    _sort(d)
    return d
