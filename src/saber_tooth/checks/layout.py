import math
from bisect import bisect_left, bisect_right
from itertools import combinations

from saber_tooth.checks.constants import VISION_MIN_DT
from saber_tooth.checks.finding import Finding
from saber_tooth.checks.walls import covers_cell
from saber_tooth.model import CUT_VECTORS, Color, Cut, Difficulty, Note
from saber_tooth.profiles import Profile
from saber_tooth.swings import MAX_CUT_ANGLE, Swing, angle_between
from saber_tooth.timing import Timing

MAX_SPREAD = 1.5
CONVERGE_SHARE = 0.4  # share of the half-jump time in which a note is still moving to its row
CONVERGE_FALLBACK_S = 0.2  # window when njs or bpm give no usable jump time
SAME_CELL_S = 0.1  # two notes in one cell closer in time than this fly through each other
SIMULTANEOUS_S = 1e-4  # notes this close are one stack, judged by the stack rules instead
MAX_HALF_JUMP_S = 18.0  # Beat Saber halves the half-jump distance until njs*spb*hjd fits this


def jump_window_s(njs: float, offset: float, bpm: float) -> float:
    """Seconds after spawn in which a note still changes row, from njs, jump offset and bpm."""
    try:
        if not (njs > 0 and bpm > 0 and math.isfinite(njs + offset + bpm)):
            return CONVERGE_FALLBACK_S
        spb = 60.0 / bpm
        hjd = 4.0
        while njs * spb * hjd > MAX_HALF_JUMP_S and hjd > 0.25:
            hjd /= 2
        return max(CONVERGE_SHARE * max(hjd + offset, 1.0) * spb, SAME_CELL_S)
    except (TypeError, ValueError):
        return CONVERGE_FALLBACK_S


def converges(dt: float, a: tuple[int, int], b: tuple[int, int], window: float) -> bool:
    """Flight paths of two notes `dt` seconds apart meet: one cell too soon, or one column
    with different rows inside the jump window."""
    dt = abs(dt)
    if dt <= SIMULTANEOUS_S:
        return False
    if a == b:
        return dt < SAME_CELL_S
    return a[0] == b[0] and VISION_MIN_DT < dt <= window


def _line_angle(u, v) -> float:
    a = angle_between(u, v)
    return min(a, 180.0 - a)


def _dist(a: Note, b: Note) -> float:
    return math.dist((a.x, a.y), (b.x, b.y))


def _spread_problem(s: Swing) -> str | None:
    if any(_dist(a, b) > MAX_SPREAD for a, b in combinations(s.notes, 2)):
        return "same-colour notes are on separate parts of the screen"
    return None


def _stack_problem(s: Swing) -> str | None:
    vecs = [CUT_VECTORS[n.cut] for n in s.notes if n.cut != Cut.ANY]
    if not vecs:  # all dots: no direction of their own, only spread counts
        return _spread_problem(s)
    if any(angle_between(u, v) > MAX_CUT_ANGLE for u, v in combinations(vecs, 2)):
        return "notes of one swing have conflicting cut directions"
    if problem := _spread_problem(s):
        return problem
    pairs = list(combinations(s.notes, 2))
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
    notes = sorted(d.notes)
    reds = [n for n in notes if n.color == Color.RED]
    blues = [n for n in notes if n.color == Color.BLUE]
    secs = [timing.to_seconds(n.beat) for n in blues]
    window = profile.warn.cross_window_s
    best: dict[Note, tuple[float, Finding]] = {}  # completing note -> closest pair
    for r in reds:
        rs = timing.to_seconds(r.beat)
        lo, hi = bisect_left(secs, rs - window), bisect_right(secs, rs + window)
        rx = r.x
        for b, bs in zip(blues[lo:hi], secs[lo:hi], strict=True):
            if rx <= b.x:  # both the far and the same-beat case need red right of blue
                continue
            same = abs(r.beat - b.beat) < 1e-6
            far = r.x - b.x >= 2 and r.x >= 2 and b.x <= 1
            if not (far or (same and r.x > b.x and r.y == b.y)):
                continue
            dt = abs(rs - bs)
            sev = "error" if dt < profile.error.cross_window_s else "warn"
            start, end = min(r.beat, b.beat), max(r.beat, b.beat)
            later = r if (r.beat, 0) > (b.beat, 1) else b
            f = Finding("crossover", d.name, start, end, sev, "hands cross over", (r, b))
            if later not in best or dt < best[later][0]:
                best[later] = (dt, f)
    return [f for _, f in best.values()]


def vision_block(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    out = []
    notes = sorted(d.notes)
    secs = [timing.to_seconds(n.beat) for n in notes]
    for i, n in enumerate(notes):
        if n.x not in (1, 2) or n.y != 1:
            continue
        for j in range(i + 1, len(notes)):
            m, dt = notes[j], secs[j] - secs[i]
            if dt > profile.warn.vision_window_s:
                break
            if dt <= VISION_MIN_DT or (m.x, m.y) == (n.x, n.y):
                continue
            sev = "error" if dt <= profile.error.vision_window_s else "warn"
            msg = "centre note blocks view of the next note"
            out.append(Finding("vision-block", d.name, n.beat, m.beat, sev, msg, (n, m)))
            break
    return out


def _in_wall(n: Note, w) -> bool:
    return covers_cell(w, n.x, n.y) and w.beat <= n.beat <= w.beat + w.duration


def note_in_wall(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    return [
        Finding("note-in-wall", d.name, n.beat, n.beat, "error", "note sits inside a wall", (n,))
        for n in d.notes
        for w in d.walls
        if _in_wall(n, w)
    ]


def note_converge(d: Difficulty, swings, timing: Timing, profile: Profile, analysis=None):
    window = jump_window_s(d.njs, d.offset, timing.initial_bpm)
    reach = max(window, SAME_CELL_S)
    out = []
    notes = sorted(d.notes)
    secs = [timing.to_seconds(n.beat) for n in notes]
    cols = [n.x for n in notes]
    last = len(notes)
    for i, n in enumerate(notes):
        si, nx = secs[i], cols[i]
        for j in range(i + 1, last):
            if secs[j] - si > reach:
                break
            if cols[j] != nx:  # converging needs one cell or one column
                continue
            m = notes[j]
            if converges(secs[j] - si, (n.x, n.y), (m.x, m.y), window):
                msg = "notes fly into the same spot while jumping to their rows"
                out.append(Finding("note-converge", d.name, n.beat, m.beat, "warn", msg, (n, m)))
    return out
