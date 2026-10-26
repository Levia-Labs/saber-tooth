from saber_tooth.mapio.errors import MapParseError
from saber_tooth.model import BasicEvent, Bomb, BpmEvent, Color, Cut, Difficulty, Note, Wall

BOOST_TYPE = 5
BPM_TYPE = 100


def _wall(w: dict) -> Wall:
    crouch = int(w.get("_type", 0)) == 1
    y, height = (2, 3) if crouch else (0, 5)
    return Wall(
        float(w["_time"]),
        int(w["_lineIndex"]),
        y,
        float(w.get("_duration", 0)),
        int(w.get("_width", 1)),
        height,
    )


def read_v2(data: dict, name: str, njs: float, offset: float, filename: str) -> Difficulty:
    d = Difficulty(name=name, njs=njs, offset=offset, filename=filename)
    try:
        for n in data.get("_notes", []):
            beat, x, y = float(n["_time"]), int(n["_lineIndex"]), int(n["_lineLayer"])
            kind = int(n["_type"])
            if kind == 3:
                d.bombs.append(Bomb(beat, x, y))
            elif kind in (0, 1):
                d.notes.append(Note(beat, x, y, Color(kind), Cut(int(n["_cutDirection"]) % 9)))
        d.walls = [_wall(w) for w in data.get("_obstacles", [])]
        for e in data.get("_events", []):
            beat, kind, value = float(e["_time"]), int(e["_type"]), int(e["_value"])
            fv = float(e.get("_floatValue", 1.0))
            if kind == BOOST_TYPE:
                d.boosts.append((beat, value == 1))
            elif kind == BPM_TYPE:
                if "_floatValue" in e and fv > 0:
                    d.bpm_events.append(BpmEvent(beat, fv))
            else:
                d.events.append(BasicEvent(beat, kind, value, fv))
        custom = data.get("_customData") or {}
        for c in custom.get("_BPMChanges", []):
            if all(b.beat != float(c["_time"]) for b in d.bpm_events):
                d.bpm_events.append(BpmEvent(float(c["_time"]), float(c["_BPM"])))
    except (KeyError, TypeError, ValueError) as exc:
        raise MapParseError(f"bad v2 difficulty {filename}: {exc!r}") from exc
    _sort(d)
    return d


def _sort(d: Difficulty) -> None:
    d.notes.sort()
    d.bombs.sort()
    d.walls.sort()
    d.events.sort()
    d.boosts.sort()
    d.bpm_events.sort()
