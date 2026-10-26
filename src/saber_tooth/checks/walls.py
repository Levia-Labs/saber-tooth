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


def blocks_standing(w: Wall) -> bool:
    """True for walls that cannot be ducked under: they cover the chest row."""
    return w.y <= 1 < w.y + w.height


def blocks_head(w: Wall) -> bool:
    """True for walls that cover the head row, crouch walls included."""
    return w.y <= 2 < w.y + w.height


def _lanes(w: Wall) -> set[int]:
    return set(range(w.x, w.x + w.width))


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
        if _trapped(chest, True) or _trapped(head, False):
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
    standing = sorted(w for w in d.walls if blocks_standing(w))
    relevant = sorted(w for w in d.walls if blocks_standing(w) or blocks_head(w))
    return _lane_findings(d, relevant) + _dodge_findings(d, standing, timing, minimum)


def wall_short(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    msg = "wall is too short to read"
    return [
        Finding("wall-short", d.name, w.beat, _end(w), "warn", msg, walls=(w,))
        for w in d.walls
        if timing.to_seconds(_end(w)) - timing.to_seconds(w.beat) < WALL_MIN_S
    ]
