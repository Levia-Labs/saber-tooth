"""Wall safety: the player must always keep room to stand and time to dodge."""

from saber_tooth.checks.finding import Finding, Severity
from saber_tooth.model import Difficulty, Wall
from saber_tooth.profiles import (
    WALL_DODGE_ERROR_SHARE,
    WALL_DODGE_S,
    WALL_MIN_S,
    Profile,
)
from saber_tooth.timing import Timing

EPS = 1e-6
DEFAULT_DODGE_S = 0.8
MIN_OVERLAP = 0.25  # lanes a decoded precision wall must cover to count for a cell


def covers(lo: float, size: float, cell: int) -> bool:
    """True when [lo, lo + size) covers more than MIN_OVERLAP of the unit cell `cell`."""
    return min(lo + size, cell + 1) - max(lo, cell) > MIN_OVERLAP


def covers_cell(w: Wall, x: int, y: int) -> bool:
    """True when the wall's decoded geometry covers grid cell (x, y)."""
    return covers(w.x, w.width, x) and covers(w.y, w.height, y)


def blocks_standing(w: Wall) -> bool:
    """True for walls that cannot be ducked under: they cover the chest row."""
    return covers(w.y, w.height, 1)


def blocks_head(w: Wall) -> bool:
    """True for walls that cover the head row, crouch walls included."""
    return covers(w.y, w.height, 2)


def is_live(w: Wall) -> bool:
    """True for walls that can touch the play space: some length, some width, a lane of 0..3.

    Zero-width and zero-length walls are wall art, not hazards, as are precision walls
    (Mapping Extensions, decoded) that overlap no cell of the 4x3 grid.
    """
    if w.duration <= 0 or not any(covers(w.x, w.width, lane) for lane in range(4)):
        return False
    return not w.me or any(covers(w.y, w.height, row) for row in range(3))


def _lanes(w: Wall) -> set[int]:
    return {lane for lane in range(4) if covers(w.x, w.width, lane)}


def _end(w: Wall) -> float:
    return w.beat + w.duration


def _trapped(blocked: set[int], centre: bool) -> bool:
    return len(blocked & {0, 1, 2, 3}) > 2 or (centre and {1, 2} <= blocked)


def _lane_findings(d: Difficulty, walls: list[Wall]) -> list[Finding]:
    out = []
    for w in walls:
        active = [o for o in walls if o.beat <= w.beat + EPS and w.beat < _end(o) - EPS]
        chest = set().union(*(_lanes(o) for o in active if blocks_standing(o)))
        head = set().union(*(_lanes(o) for o in active if blocks_head(o)))
        # A lane is lost only when neither standing (head row) nor ducking (chest row) clears it.
        if _trapped(chest & head, True):
            msg = "walls leave the player fewer than 2 free lanes or the centre blocked"
            out.append(Finding("wall-trap", d.name, w.beat, _end(w), "error", msg, walls=(w,)))
    return out


def _dodge_side(w: Wall) -> str | None:
    lanes = _lanes(w)
    if 1 in lanes and 2 not in lanes:
        return "left"
    return "right" if 2 in lanes and 1 not in lanes else None


def _dodge_findings(d: Difficulty, walls: list[Wall], timing: Timing, minimum: float):
    out = []
    forcing = [(w, _dodge_side(w)) for w in walls if _dodge_side(w)]
    for i, (a, side_a) in enumerate(forcing):
        end = timing.to_seconds(_end(a))
        for b, side_b in forcing[i + 1 :]:
            gap = timing.to_seconds(b.beat) - end
            if gap >= minimum:
                break
            if side_a == side_b or gap < 0:
                continue
            sev: Severity = "error" if gap < minimum * WALL_DODGE_ERROR_SHARE else "warn"
            msg = f"only {gap:.2f}s to dodge to the other side (needs {minimum:.2f}s)"
            out.append(Finding("wall-trap", d.name, b.beat, _end(b), sev, msg, walls=(b,)))
    return out


def wall_trap(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    minimum = WALL_DODGE_S.get(profile.name, DEFAULT_DODGE_S)
    live = [w for w in d.walls if is_live(w)]
    standing = sorted(w for w in live if blocks_standing(w))
    relevant = sorted(w for w in live if blocks_standing(w) or blocks_head(w))
    return _lane_findings(d, relevant) + _dodge_findings(d, standing, timing, minimum)


def wall_short(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    msg = "wall is too short to read"
    return [
        Finding("wall-short", d.name, w.beat, _end(w), "warn", msg, walls=(w,))
        for w in d.walls
        if is_live(w) and timing.to_seconds(_end(w)) - timing.to_seconds(w.beat) < WALL_MIN_S
    ]
