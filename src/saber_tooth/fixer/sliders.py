"""Keep raw v3 arcs and chains consistent when a note they reference is edited."""

from saber_tooth.model import Difficulty, Note

EPS = 1e-6
KEYS = ("sliders", "burstSliders")


def _at(s: dict, note: Note, b: str, x: str, y: str) -> bool:
    try:
        same_cell = int(s[x]) == note.x and int(s[y]) == note.y
        return same_cell and abs(float(s[b]) - note.beat) < EPS and int(s["c"]) == int(note.color)
    except (KeyError, TypeError, ValueError):
        return False


def _tail(s: dict, note: Note, key: str) -> bool:
    """Only arcs end on a note; a chain's tail is a bare position and never matches."""
    return key == "sliders" and _at(s, note, "tb", "tx", "ty")


def _moved(s: dict, note: Note, new: Note, key: str) -> dict:
    out = dict(s)
    if _at(s, note, "b", "x", "y"):
        out.update(x=new.x, y=new.y, d=int(new.cut))
    if _tail(s, note, key):
        out.update(tx=new.x, ty=new.y)
        if "tc" in out:
            out["tc"] = int(new.cut)
    return out


def retarget(d: Difficulty, note: Note, new: Note | None) -> None:
    """Point every arc/chain end that references `note` at `new`; drop it when `new` is None
    or has the other colour (an arc joins notes of one hand)."""
    if new is not None and new.color != note.color:
        new = None
    for key in KEYS:
        if key not in d.raw:
            continue
        kept = []
        for s in d.raw[key]:
            ends = isinstance(s, dict) and (_at(s, note, "b", "x", "y") or _tail(s, note, key))
            if not ends:
                kept.append(s)
            elif new is not None:
                kept.append(_moved(s, note, new, key))
        d.raw[key] = kept
