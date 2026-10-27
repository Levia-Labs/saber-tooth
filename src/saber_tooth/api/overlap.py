"""Which open proposals of one difficulty touch the same notes."""

from collections import defaultdict

OPEN = ("pending", "approved", "applying")
BEAT_DIGITS = 4


def _key(difficulty: str, n: dict) -> tuple:
    return (difficulty, round(float(n["beat"]), BEAT_DIGITS), n["x"], n["y"], n["color"])


def _touch(proposal: dict) -> tuple[set[tuple], list[tuple[str, float, float]], list[tuple]]:
    """(note keys, fill ranges, note beats) of a proposal's ops; unreadable ops are skipped."""
    keys: set[tuple] = set()
    ranges: list[tuple[str, float, float]] = []
    beats: list[tuple] = []
    for op in proposal.get("ops") or []:
        try:
            diff = op["difficulty"]
            if op["op"] == "fill":
                ranges.append((diff, float(op["beat_start"]), float(op["beat_end"])))
                keys.update(_key(diff, n) for n in op["notes"])
            elif "note" in op:
                keys.add(_key(diff, op["note"]))
                beats.append((diff, float(op["note"]["beat"])))
        except (KeyError, TypeError, ValueError):
            continue
    return keys, ranges, beats


def conflicts_with(proposals: list[dict]) -> dict[int, list[int]]:
    """For each open proposal, the ids of other open ones of its difficulty that share a note
    (same beat, position and colour) or whose fill range contains one of its notes."""
    touched = {p["id"]: _touch(p) for p in proposals if p["status"] in OPEN}
    by_key: dict[tuple, set[int]] = defaultdict(set)
    for pid, (keys, _, _) in touched.items():
        for k in keys:
            by_key[k].add(pid)
    out: dict[int, set[int]] = defaultdict(set)
    for ids in by_key.values():
        for a in ids:
            out[a] |= ids - {a}
    for pid, (_, ranges, _) in touched.items():
        for diff, lo, hi in ranges:
            for other, (_, _, beats) in touched.items():
                if other != pid and any(d == diff and lo <= b <= hi for d, b in beats):
                    out[pid].add(other)
                    out[other].add(pid)
    return {pid: sorted(ids) for pid, ids in out.items() if ids}
