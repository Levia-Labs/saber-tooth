import math
from itertools import pairwise

from saber_tooth.checks.finding import Finding, grade_above, grade_below
from saber_tooth.model import Bomb, Color, Difficulty
from saber_tooth.profiles import Profile
from saber_tooth.swings import Swing
from saber_tooth.timing import Timing


def _pairs(swings):
    for hand in (Color.RED, Color.BLUE):
        hand_swings = swings[hand]
        yield from pairwise(hand_swings)


def _bomb_between(bombs: list[Bomb], a: Swing, b: Swing) -> bool:
    xs = (0, 1, 2) if a.hand == Color.RED else (1, 2, 3)
    return any(a.beat < bomb.beat < b.beat and bomb.x in xs for bomb in bombs)


def _make(rule, d, a: Swing, b: Swing, severity, message) -> Finding:
    return Finding(rule, d.name, a.beat, b.beat, severity, message, a.notes + b.notes)


def parity_break(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    out = []
    for a, b in _pairs(swings):
        if a.vector is None or b.vector is None:
            continue
        if a.vector[0] * b.vector[0] + a.vector[1] * b.vector[1] <= 0.1:
            continue
        if _bomb_between(d.bombs, a, b):
            continue
        dt = b.seconds - a.seconds
        sev = grade_below(dt, profile.error.reset_window_s, profile.warn.reset_window_s)
        if sev:
            msg = f"same swing direction twice in {dt:.2f}s"
            out.append(_make("parity-break", d, a, b, sev, msg))
    return out


def wide_jump(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    out = []
    for a, b in _pairs(swings):
        dt = max(b.seconds - a.seconds, 1e-6)
        speed = math.dist(a.end, b.start) / dt
        sev = grade_above(speed, profile.error.max_hand_speed, profile.warn.max_hand_speed)
        if sev:
            out.append(_make("wide-jump", d, a, b, sev, f"hand travels {speed:.1f} cells/s"))
    return out


def swing_speed(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    out = []
    for a, b in _pairs(swings):
        dt = b.seconds - a.seconds
        sev = grade_below(dt, profile.error.min_hand_gap_s, profile.warn.min_hand_gap_s)
        if sev:
            out.append(_make("swing-speed", d, a, b, sev, f"swings only {dt:.3f}s apart"))
    return out
