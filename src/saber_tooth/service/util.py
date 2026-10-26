"""Pure helpers: map ids, finding keys and op spans."""

import hashlib

from saber_tooth.checks import Finding
from saber_tooth.fixer.codec import note_from_dict
from saber_tooth.fixer.ops import Fill, Op, op_from_dict

EPS = 1e-6
Span = tuple[str, float, float]


def map_id_for(folder: str) -> str:
    return hashlib.sha256(folder.encode("utf-8")).hexdigest()[:12]


def finding_from_dict(d: dict) -> Finding:
    return Finding(
        d["rule"],
        d["difficulty"],
        float(d["beat_start"]),
        float(d["beat_end"]),
        d["severity"],
        d["message"],
        tuple(note_from_dict(n) for n in d["notes"]),
    )


def span(op: Op) -> Span | None:
    if isinstance(op, Fill):
        return (op.difficulty, op.beat_start, op.beat_end)
    note = getattr(op, "note", None)
    if note is None:
        return None
    return (op.difficulty, note.beat, note.beat)


def overlaps(a: Span, b: Span) -> bool:
    if "*" not in (a[0], b[0]) and a[0] != b[0]:
        return False
    return a[1] <= b[2] + EPS and b[1] <= a[2] + EPS


def related(spans: list[Span], proposals: list[dict]) -> list[int]:
    """Ids of proposals whose ops touch any span; unreadable ops are skipped."""
    ids = []
    for p in proposals:
        try:
            mine = [s for s in (span(op_from_dict(o)) for o in p["ops"]) if s]
        except (KeyError, ValueError, TypeError):
            continue
        if any(overlaps(a, b) for a in mine for b in spans):
            ids.append(p["id"])
    return ids
