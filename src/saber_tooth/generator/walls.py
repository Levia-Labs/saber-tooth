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
FLAT_BARS = 8  # phrase boundary spacing for songs without calm or build-up sections
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


def _side_wall(notes, start, beats, pref, margin=NOTE_MARGIN, both=True) -> Wall | None:
    """A side wall on the preferred side, else (`both`) the other, where no note shares the lane."""
    for side in (pref, 1 - pref) if both else (pref,):
        x = 3 * side
        if not _busy(notes, range(x, x + 1), start - margin, start + beats + margin):
            return Wall(start, x, 0, beats, 1, 5)
    return None


def _flat(energy: dict[int, float]) -> bool:
    """True when no bar is calm and none ends a build-up: the song has no sections to mark."""
    return not any(0.0 < e < CALM_ENERGY or _build_up(energy, bar) for bar, e in energy.items())


def _clashes(start: float, walls: list[Wall], spacing: float) -> bool:
    return any(w.beat - spacing < start < w.beat + max(w.duration, spacing) for w in walls)


def _flat_wall(notes, bar, start, flip, rng) -> Wall | None:
    """First start within the boundary bar whose side lane is free: the hands are opposite."""
    beats = float(rng.choice((1, 2)))
    side = (bar // FLAT_BARS + flip) % 2
    for shift in range(int(BAR_BEATS)):
        wall = _side_wall(notes, start + shift, beats, side, both=False)
        if wall is not None:
            return wall
    return None


def _section_wall(notes, bar, start, build, crouch_ok, flip, rng) -> Wall | None:
    if crouch_ok and rng.random() < CROUCH_CHANCE:
        lo, hi = start - CROUCH_MARGIN, start + CROUCH_BEATS + CROUCH_MARGIN
        if not _busy(notes, range(4), lo, hi):
            return Wall(start, 1, 2, CROUCH_BEATS, 2, 3)
    beats = float(rng.choice((1, 2) if build else (2, 3, 4)))
    return _side_wall(notes, start, beats, (bar // PHRASE_BARS + flip) % 2)


def place_walls(
    notes: list[Note],
    stats: BarStats,
    phase: float,
    profile: Profile,
    seed: int,
    span: tuple[float, float] | None = None,
    existing: tuple[Wall, ...] | list[Wall] = (),
) -> list[Wall]:
    """Deterministic per seed; empty for tiers below Hard. Calm passages and build-ups get
    walls; a flat song gets sparse ones on phrase boundaries. `span` (beats) confines new walls
    and `existing` walls keep their spacing."""
    if profile.name not in WALL_TIERS:
        return []
    rng = random.Random(f"{seed}:{profile.name}:walls")  # noqa: S311 # nosec B311 - layout, not security
    flip = rng.randrange(2)
    walls: list[Wall] = []
    last_start, last_end, last_crouch = -1e9, -1e9, -1e9
    flat = _flat(stats.energy)
    spacing = SPACING[profile.name]
    for bar in sorted(stats.energy):
        calm = 0.0 < stats.energy[bar] < CALM_ENERGY
        build = _build_up(stats.energy, bar)
        start = phase + BAR_BEATS * bar
        mark = bar > 0 and bar % FLAT_BARS == 0 if flat else calm or build
        outside = span is not None and not span[0] <= start < span[1]
        if not mark or start - last_start < spacing or start < last_end or outside:
            continue
        if _clashes(start, [*existing], spacing):
            continue
        if flat:
            wall = _flat_wall(notes, bar, start, flip, rng)
        else:
            crouch_ok = profile.name in CROUCH_TIERS and build
            crouch_ok = crouch_ok and start - last_crouch >= CROUCH_SPACING
            wall = _section_wall(notes, bar, start, build, crouch_ok, flip, rng)
        if wall is None or (span and wall.beat + wall.duration > span[1]):
            continue
        walls.append(wall)
        last_start, last_end = wall.beat, wall.beat + wall.duration
        if wall.y == 2:
            last_crouch = wall.beat
    return walls
