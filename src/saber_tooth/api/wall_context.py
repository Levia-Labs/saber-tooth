"""Walls around a proposal: the ones it changes and the stored ones that frame them."""

from pathlib import Path

from saber_tooth.fixer.codec import wall_to_dict
from saber_tooth.mapio import MapParseError, load_map

CONTEXT_BEATS = 2.0


def changed_walls(proposal: dict) -> tuple[list[dict], list[dict]]:
    """(walls_before, walls_after): walls the proposal's ops delete or replace, and add."""
    before: list[dict] = []
    after: list[dict] = []
    for op in proposal.get("ops") or []:
        if op.get("op") == "delete-wall":
            before.append(dict(op["wall"]))
        elif op.get("op") == "fill":
            before.extend(dict(w) for w in op.get("walls_removed", []))
            after.extend(dict(w) for w in op.get("walls_added", []))
    return before, after


def _window(proposal: dict, walls: list[dict]) -> tuple[float, float] | None:
    sides = [proposal[k] for k in ("before", "after") if isinstance(proposal[k], list)]
    spans = [(n["beat"], n["beat"]) for side in sides for n in side]
    spans += [(w["beat"], w["beat"] + w["duration"]) for w in walls]
    for op in proposal.get("ops") or []:
        if op.get("op") == "fill":
            spans.append((op["beat_start"], op["beat_end"]))
    if not spans:
        return None
    return min(s[0] for s in spans) - CONTEXT_BEATS, max(s[1] for s in spans) + CONTEXT_BEATS


def stored_walls(folder: Path) -> dict[str, list[dict]]:
    """Walls of every difficulty of the map in `folder`; empty when it cannot be read."""
    try:
        beatmap = load_map(folder)
    except (MapParseError, OSError):
        return {}
    return {n: [wall_to_dict(w) for w in d.walls] for n, d in beatmap.difficulties.items()}


def walls_context(proposal: dict, stored: dict[str, list[dict]], shown: list[dict]) -> list[dict]:
    """Stored walls of the proposal's difficulty overlapping its window (+- 2 beats),
    excluding the walls already `shown` as before or after."""
    window = _window(proposal, shown)
    if window is None:
        return []
    lo, hi = window
    return [
        w
        for w in stored.get(proposal["difficulty"], [])
        if w["beat"] <= hi and w["beat"] + w["duration"] >= lo and w not in shown
    ]
