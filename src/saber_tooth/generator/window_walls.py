"""Walls of a window regeneration: keep what the new notes leave alone, add what fits."""

from saber_tooth.checks import check_difficulty
from saber_tooth.generator.candidates import BarStats
from saber_tooth.generator.walls import place_walls
from saber_tooth.model import Difficulty, Note, Wall
from saber_tooth.profiles import Profile
from saber_tooth.timing import Timing

WALL_RULES = {"wall-trap", "wall-short", "note-in-wall"}


def _inside(n: Note, w: Wall) -> bool:
    in_x, in_y = w.x <= n.x < w.x + w.width, w.y <= n.y < w.y + w.height
    return in_x and in_y and w.beat <= n.beat <= w.beat + w.duration


def _keys(d: Difficulty, timing: Timing, profile: Profile) -> set[tuple]:
    found = check_difficulty(d, timing, profile, None, WALL_RULES)
    return {(f.rule, f.beat_start, f.beat_end) for f in found}


def window_walls(
    notes: list[Note],
    existing: list[Wall],
    bars: BarStats,
    phase: float,
    profile: Profile,
    seed: int,
    span: tuple[float, float],
    timing: Timing,
) -> list[Wall]:
    """The merged walls: `existing` minus those a note now sits in, plus new walls inside
    `span` (beats). A new wall that adds any wall finding to the merge is dropped."""
    kept = [w for w in existing if not any(_inside(n, w) for n in notes)]
    d = Difficulty(profile.name, profile.njs, profile.offset, notes=notes, walls=list(kept))
    baseline = _keys(d, timing, profile)
    for wall in place_walls(notes, bars, phase, profile, seed, span, kept):
        d.walls = sorted([*d.walls, wall])
        if _keys(d, timing, profile) - baseline:
            d.walls.remove(wall)
    return d.walls
