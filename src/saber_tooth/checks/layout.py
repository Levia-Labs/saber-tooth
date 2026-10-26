import math
from bisect import bisect_left, bisect_right
from itertools import combinations

from saber_tooth.checks.finding import Finding
from saber_tooth.model import CUT_VECTORS, Color, Cut, Difficulty, Note
from saber_tooth.profiles import Profile
from saber_tooth.swings import Swing
from saber_tooth.timing import Timing

MAX_CUT_ANGLE = 45.5  # 45 degrees plus tolerance for the rounded diagonal vectors
MAX_SPREAD = 1.5


def _angle(u, v) -> float:
    cos = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def _line_angle(u, v) -> float:
    a = _angle(u, v)
    return min(a, 180.0 - a)


def _dist(a: Note, b: Note) -> float:
    return math.dist((a.x, a.y), (b.x, b.y))


def _stack_problem(s: Swing) -> str | None:
    vecs = [CUT_VECTORS[n.cut] for n in s.notes if n.cut != Cut.ANY]
    if any(_angle(u, v) > MAX_CUT_ANGLE for u, v in combinations(vecs, 2)):
        return "notes of one swing have conflicting cut directions"
    pairs = list(combinations(s.notes, 2))
    if any(_dist(a, b) > MAX_SPREAD for a, b in pairs):
        return "same-colour notes are on separate parts of the screen"
    a, b = max(pairs, key=lambda p: _dist(*p))
    line = (b.x - a.x, b.y - a.y)
    if s.vector and any(line) and _line_angle(line, s.vector) > MAX_CUT_ANGLE:
        return "stack is not aligned with the swing direction"
    return None


def stack_conflict(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    out = []
    for hand in (Color.RED, Color.BLUE):
        for s in swings[hand]:
            problem = _stack_problem(s) if len(s.notes) > 1 else None
            if problem:
                f = Finding("stack-conflict", d.name, s.beat, s.beat, "error", problem, s.notes)
                out.append(f)
    return out


def crossover(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    reds = [n for n in d.notes if n.color == Color.RED]
    blues = [n for n in d.notes if n.color == Color.BLUE]
    secs = [timing.to_seconds(n.beat) for n in blues]
    window = profile.warn.cross_window_s
    out = []
    for r in reds:
        rs = timing.to_seconds(r.beat)
        lo, hi = bisect_left(secs, rs - window), bisect_right(secs, rs + window)
        for b, bs in zip(blues[lo:hi], secs[lo:hi], strict=True):
            same = abs(r.beat - b.beat) < 1e-6
            far = r.x - b.x >= 2 and r.x >= 2 and b.x <= 1
            if not (far or (same and r.x > b.x and r.y == b.y)):
                continue
            sev = "error" if abs(rs - bs) <= profile.error.cross_window_s else "warn"
            start, end = min(r.beat, b.beat), max(r.beat, b.beat)
            out.append(Finding("crossover", d.name, start, end, sev, "hands cross over", (r, b)))
    return out


def vision_block(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    out = []
    notes = d.notes
    secs = [timing.to_seconds(n.beat) for n in notes]
    for i, n in enumerate(notes):
        if n.x not in (1, 2) or n.y != 1:
            continue
        for j in range(i + 1, len(notes)):
            m, dt = notes[j], secs[j] - secs[i]
            if dt > profile.warn.vision_window_s:
                break
            if dt <= 0.05 or (m.x, m.y) == (n.x, n.y):
                continue
            sev = "error" if dt <= profile.error.vision_window_s else "warn"
            msg = "centre note blocks view of the next note"
            out.append(Finding("vision-block", d.name, n.beat, m.beat, sev, msg, (n, m)))
            break
    return out


def _in_wall(n: Note, w) -> bool:
    in_x = w.x <= n.x < w.x + w.width
    in_y = w.y <= n.y < w.y + w.height
    return in_x and in_y and w.beat <= n.beat <= w.beat + w.duration


def note_in_wall(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    return [
        Finding("note-in-wall", d.name, n.beat, n.beat, "error", "note sits inside a wall", (n,))
        for n in d.notes
        for w in d.walls
        if _in_wall(n, w)
    ]
