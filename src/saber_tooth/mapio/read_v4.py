from saber_tooth.mapio.errors import MapParseError
from saber_tooth.mapio.read_v2 import _sort
from saber_tooth.mapio.vanilla import vanilla_cell, vanilla_cut
from saber_tooth.model import BasicEvent, Bomb, Color, Difficulty, Note, Wall

# TODO(v4): bpm data and v4 light box groups are ignored in v1.


def _lookup(data: dict, key: str, idx: int) -> dict:
    return data[key][idx]


def _i(e: dict, key: str) -> int:
    """Beat Saber omits zero-valued fields, so a missing integer field is 0."""
    return int(e.get(key, 0))


def _f(e: dict, key: str) -> float:
    return float(e.get(key, 0))


def read_v4(
    data: dict, lightshow: dict | None, name: str, njs: float, offset: float, filename: str
) -> Difficulty:
    d = Difficulty(name=name, njs=njs, offset=offset, filename=filename)
    try:
        for n in data.get("colorNotes", []):
            e = _lookup(data, "colorNotesData", _i(n, "i"))
            d.notes.append(
                Note(
                    _f(n, "b"),
                    *vanilla_cell(_i(e, "x"), _i(e, "y")),
                    Color(_i(e, "c")),
                    vanilla_cut(_i(e, "d")),
                    int(e.get("a", 0)),
                )
            )
        for b in data.get("bombNotes", []):
            e = _lookup(data, "bombNotesData", _i(b, "i"))
            d.bombs.append(Bomb(_f(b, "b"), *vanilla_cell(_i(e, "x"), _i(e, "y"))))
        for w in data.get("obstacles", []):
            e = _lookup(data, "obstaclesData", _i(w, "i"))
            x, y, dur = _i(e, "x"), _i(e, "y"), _f(e, "d")
            d.walls.append(Wall(_f(w, "b"), x, y, dur, _i(e, "w"), _i(e, "h")))
        for ev in (lightshow or {}).get("basicEvents", []):
            e = _lookup(lightshow, "basicEventsData", _i(ev, "i"))
            fv = float(e.get("f", 1.0))
            d.events.append(BasicEvent(_f(ev, "b"), _i(e, "t"), _i(e, "i"), fv))
    except MapParseError:
        raise
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MapParseError(f"bad v4 difficulty {filename}: {exc!r}") from exc
    _sort(d)
    return d
