"""Walls only: side walls on calm passages and build-ups, rare crouch walls on top tiers.

Walls are placed after the notes are final and only where no note shares their lanes, so
they cannot trigger `note-in-wall` or `wall-trap` by construction.
"""

import random
from itertools import pairwise

from saber_tooth.generator.candidates import BAR_BEATS, BarStats
from saber_tooth.model import Note, Wall
from saber_tooth.profiles import WALL_TIERS, Profile

CALM_ENERGY = 0.45  # bars below this (but not silent) are calm
BUILD_BARS = 4  # energy must rise over this many bars to count as a build-up
BUILD_RISE = 0.25
BUILD_DIP = 0.05  # tolerated drop between neighbouring bars inside a build-up
NOTE_MARGIN = 0.5  # beats kept free of notes around a side wall
CROUCH_MARGIN = 0.25
CROUCH_BEATS = 2.0
CROUCH_SPACING = 4 * BAR_BEATS
PHRASE_BARS = 4
# Minimum beats between the starts of two walls: Hard at most one wall per two bars.
SPACING = {"Hard": 2 * BAR_BEATS, "Expert": 1.5 * BAR_BEATS, "ExpertPlus": BAR_BEATS}
CROUCH_TIERS = ("ExpertPlus",)
CROUCH_CHANCE = 0.5


def _build_up(energy: dict[int, float], bar: int) -> bool:
    run = [energy.get(b) for b in range(bar - BUILD_BARS + 1, bar + 1)]
    if any(e is None for e in run):
        return False
    steps = pairwise(run)
    return run[-1] - run[0] >= BUILD_RISE and all(b - a >= -BUILD_DIP for a, b in steps)


def _busy(notes: list[Note], lanes: range, lo: float, hi: float) -> bool:
    return any(lo <= n.beat <= hi and n.x in lanes for n in notes)


def _side_wall(notes, start, beats, pref, margin=NOTE_MARGIN) -> Wall | None:
    for side in (pref, 1 - pref):
        x = 3 * side
        if not _busy(notes, range(x, x + 1), start - margin, start + beats + margin):
            return Wall(start, x, 0, beats, 1, 5)
    return None


def place_walls(
    notes: list[Note], stats: BarStats, phase: float, profile: Profile, seed: int
) -> list[Wall]:
    """Deterministic per seed; empty for tiers below Hard."""
    if profile.name not in WALL_TIERS:
        return []
    rng = random.Random(f"{seed}:{profile.name}:walls")  # noqa: S311 - layout, not security
    flip = rng.randrange(2)
    walls: list[Wall] = []
    last_start, last_end, last_crouch = -1e9, -1e9, -1e9
    for bar in sorted(stats.energy):
        calm = 0.0 < stats.energy[bar] < CALM_ENERGY
        build = _build_up(stats.energy, bar)
        start = phase + BAR_BEATS * bar
        if not (calm or build) or start - last_start < SPACING[profile.name] or start < last_end:
            continue
        wall = None
        crouch_ok = profile.name in CROUCH_TIERS and build and start - last_crouch >= CROUCH_SPACING
        if crouch_ok and rng.random() < CROUCH_CHANCE:
            lo, hi = start - CROUCH_MARGIN, start + CROUCH_BEATS + CROUCH_MARGIN
            if not _busy(notes, range(4), lo, hi):
                wall = Wall(start, 1, 2, CROUCH_BEATS, 2, 3)
                last_crouch = start
        if wall is None:
            beats = float(rng.choice((1, 2) if build else (2, 3, 4)))
            wall = _side_wall(notes, start, beats, (bar // PHRASE_BARS + flip) % 2)
        if wall is not None:
            walls.append(wall)
            last_start, last_end = wall.beat, wall.beat + wall.duration
    return walls
