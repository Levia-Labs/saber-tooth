from saber_tooth.mapio.errors import MapParseError
from saber_tooth.mapio.read_v2 import _sort
from saber_tooth.model import BasicEvent, Bomb, Color, Cut, Difficulty, Note, Wall

# TODO(v4): bpm data and v4 light box groups are ignored in v1.


def _lookup(data: dict, key: str, idx: int) -> dict:
    return data[key][idx]


def read_v4(
    data: dict, lightshow: dict | None, name: str, njs: float, offset: float, filename: str
) -> Difficulty:
    d = Difficulty(name=name, njs=njs, offset=offset, filename=filename)
    try:
        for n in data.get("colorNotes", []):
            e = _lookup(data, "colorNotesData", int(n["i"]))
            d.notes.append(
                Note(
                    float(n["b"]),
                    int(e["x"]),
                    int(e["y"]),
                    Color(int(e["c"])),
                    Cut(int(e["d"]) % 9),
                    int(e.get("a", 0)),
                )
            )
        for b in data.get("bombNotes", []):
            e = _lookup(data, "bombNotesData", int(b["i"]))
            d.bombs.append(Bomb(float(b["b"]), int(e["x"]), int(e["y"])))
        for w in data.get("obstacles", []):
            e = _lookup(data, "obstaclesData", int(w["i"]))
            x, y, dur = int(e["x"]), int(e["y"]), float(e["d"])
            d.walls.append(Wall(float(w["b"]), x, y, dur, int(e["w"]), int(e["h"])))
        for ev in (lightshow or {}).get("basicEvents", []):
            e = _lookup(lightshow, "basicEventsData", int(ev["i"]))
            fv = float(e.get("f", 1.0))
            d.events.append(BasicEvent(float(ev["b"]), int(e["t"]), int(e["i"]), fv))
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MapParseError(f"bad v4 difficulty {filename}: {exc!r}") from exc
    _sort(d)
    return d
