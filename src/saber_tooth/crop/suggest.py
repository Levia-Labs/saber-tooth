"""Auto crop: rank 1 and 2 minute windows by how good they are to play and keep the best three.

Windows start and end on bar lines. A window is scored in points out of 100 on the smoothed
notes-per-second curve of the hardest difficulty (peak, rise, release, quiet cut points), on every
difficulty's mean density (comfort), on empty gaps, on variety, on how close it is to its target
length and on valleys: both cuts sit where the audio is low and no difficulty has notes. A coarse
grid of windows seeds a search that moves each bound by bars and phrases, keeps the best and
stops when a pass finds nothing better. Windows below MIN_POINTS are never returned. Pure and
deterministic: the same inputs give the same list.
"""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import accumulate

from saber_tooth.crop.valley import audio_reference, cut_valley, prefix

TARGETS = (60, 120)
TOLERANCE_S = {60: 10.0, 120: 15.0}  # a window may stray this far from its target: a phrase or two
SMOOTH_BINS = 5  # a 5 s moving average: single flurries do not count as the peak
RISE_BINS = 10  # the build-up is judged on the first 10 s after the start
CUT_BINS = 3  # the entry and the exit on the 3 s next to the cut
BLOCK_BINS = 8  # variety is measured on 8 s blocks
CALM = 0.45  # a point is "calm" when it is below this share of the window peak
MAX_GAP_S = 8  # an empty stretch up to this long is fine; more than that costs the gap score
COMFORT_LO, COMFORT_FULL, COMFORT_TOP, COMFORT_MAX = 0.8, 1.5, 5.5, 9.0  # window mean NPS ramp
PEAK_ZONE = (0.30, 0.80)  # the peak sits best between 30 % and 80 % of the way through
MAX_OVERLAP = 0.5  # of the shorter pick; picks may share at most this much
COUNT = 3
MIN_POINTS = 70.0  # a window scoring less is never proposed
SEED_STEP = 4  # the seed grid takes every 4th bar line as a start and as an end
SEED_KEEP = 12  # the best seeds each pass refines
MOVES = (1, 2, 4, 8)  # a bound moves by this many bars: a bar, two, a half phrase, a phrase
MAX_PASSES = 8
POINTS = {  # key: (label, points out of 100); the points sum to 100
    "peak": ("Peak intensity", 22.0),  # window peak against the song peak
    "arc": ("Rise and release", 18.0),  # build-up before and release after the peak
    "valley": ("Valley cuts", 18.0),  # both cuts in quiet audio with no notes near them
    "position": ("Peak position", 8.0),  # the peak in the middle zone, not at an edge
    "comfort": ("Playable density", 8.0),  # mean NPS in a playable range on every difficulty
    "gaps": ("No long gaps", 8.0),  # no long empty stretch
    "variety": ("Variety", 8.0),  # the energy changes from block to block
    "cut": ("Cut on a phrase", 6.0),  # quiet entry and exit, cuts on section or phrase lines
    "length": ("Target length", 4.0),  # close to the target length
}
WEIGHTS = {k: pts / 100.0 for k, (_, pts) in POINTS.items()}


@dataclass(frozen=True)
class Part:
    key: str
    label: str
    points: float
    max_points: float


@dataclass(frozen=True)
class Suggestion:
    start_beat: float
    end_beat: float
    start_s: float
    end_s: float
    target_s: int
    score: float  # points out of 100: the sum of the breakdown
    reason: str
    breakdown: tuple[Part, ...] = ()

    @property
    def length_s(self) -> float:
        return self.end_s - self.start_s


def _smooth(series: list[float]) -> list[float]:
    half = SMOOTH_BINS // 2
    pre = [0.0, *accumulate(series)]
    n = len(series)
    return [
        (pre[min(n, i + half + 1)] - pre[max(0, i - half)])
        / (min(n, i + half + 1) - max(0, i - half))
        for i in range(n)
    ]


def _ramp(x: float, lo: float, hi: float) -> float:
    return 0.0 if x <= lo else 1.0 if x >= hi else (x - lo) / (hi - lo)


def _comfort(mean: float) -> float:
    return _ramp(mean, COMFORT_LO, COMFORT_FULL) * (1.0 - _ramp(mean, COMFORT_TOP, COMFORT_MAX))


def _position(pos: float) -> float:
    lo, hi = PEAK_ZONE
    if lo <= pos <= hi:
        return 1.0
    return max(0.0, 1.0 - (lo - pos if pos < lo else pos - hi) / lo)


def _stamp(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _reason(sm: list[float], i0: int, i1: int, peak_i: int, start_s: float, end_s: float) -> str:
    top = sm[peak_i]
    rise = start_s
    for i in range(peak_i, i0 - 1, -1):
        if sm[i] <= CALM * top:
            rise = float(i)
            break
    release = end_s
    for i in range(peak_i, i1):
        if sm[i] <= CALM * top:
            release = float(i)
            break
    return f"rise from {_stamp(rise)}, peak at {_stamp(peak_i)}, release at {_stamp(release)}"


def _mean(pre: list[float], a: int, b: int) -> float:
    return (pre[b] - pre[a]) / (b - a) if b > a else 0.0


def score_window(
    sm: list[float],
    sm_pre: list[float],
    raw: list[float],
    pres: list[list[float]],
    song_peak: float,
    i0: int,
    i1: int,
    target_s: int,
    aligned: float,
    valley: float = 1.0,
) -> tuple[list[Part], int]:
    """Return (points per component, bin of the window peak) for the bins [i0, i1)."""
    n = i1 - i0
    peak_i = max(range(i0, i1), key=lambda i: (sm[i], -i))
    top = sm[peak_i]
    if top <= 0 or song_peak <= 0:
        return [Part(k, lab, 0.0, pts) for k, (lab, pts) in POINTS.items()], peak_i
    rise_lvl = _mean(sm_pre, i0, min(i1, i0 + RISE_BINS))
    exit_lvl = _mean(sm_pre, max(i0, i1 - RISE_BINS), i1)
    arc = min(1.0, (top - rise_lvl) / top, (top - exit_lvl) / top)
    quiet = 1.0 - (
        _mean(sm_pre, i0, min(i1, i0 + CUT_BINS)) + _mean(sm_pre, max(i0, i1 - CUT_BINS), i1)
    ) / (2 * top)
    run = gap = 0
    for v in raw[i0:i1]:
        run = run + 1 if v == 0 else 0
        gap = max(gap, run)
    blocks = [_mean(sm_pre, a, min(i1, a + BLOCK_BINS)) for a in range(i0, i1, BLOCK_BINS)]
    avg = sum(blocks) / len(blocks)
    cv = (sum((b - avg) ** 2 for b in blocks) / len(blocks)) ** 0.5 / avg if avg > 0 else 0.0
    comfort = sum(_comfort(_mean(p, i0, i1)) for p in pres) / len(pres)
    parts = {
        "peak": min(1.0, top / song_peak),
        "arc": max(0.0, arc),
        "position": _position((peak_i - i0) / n),
        "comfort": comfort,
        "gaps": 1.0 - _ramp(gap, MAX_GAP_S, MAX_GAP_S * 4),
        "variety": min(1.0, cv / 0.5),
        "cut": 0.7 * max(0.0, min(1.0, quiet)) + 0.3 * aligned,
        "length": 1.0 - min(1.0, abs(n - target_s) / TOLERANCE_S[target_s]),
        "valley": max(0.0, min(1.0, valley)),
    }
    return [
        Part(k, lab, round(pts * max(0.0, min(1.0, parts[k])), 1), pts)
        for k, (lab, pts) in POINTS.items()
    ], peak_i


def _overlap(a: Suggestion, b: Suggestion) -> float:
    shared = min(a.end_s, b.end_s) - max(a.start_s, b.start_s)
    return max(0.0, shared) / min(a.length_s, b.length_s)


def _target_of(length_s: float) -> int | None:
    for target in TARGETS:
        if abs(length_s - target) <= TOLERANCE_S[target] + 1e-9:
            return target
    return None


def suggest_crops(
    series: dict[str, list[float]],
    hardest: str,
    bars: list[float],
    to_seconds: Callable[[float], float],
    boundaries: list[float],
    duration_s: float,
    audio: list[float] | None = None,
) -> list[Suggestion]:
    """The best distinct windows (at most COUNT, each at least MIN_POINTS), best first. `bars` are
    bar-line beats; `audio` is the weighted onsets per 1 s bin, empty or None when not analysed."""
    raw = series.get(hardest, [])
    if not raw or len(bars) < 2:
        return []
    sm = _smooth(raw)
    sm_pre = [0.0, *accumulate(sm)]
    pres = [[0.0, *accumulate(s)] for s in series.values()]
    note_pre = prefix([sum(col) for col in zip(*series.values(), strict=False)])
    audio_pre = prefix(audio) if audio else []
    audio_ref = audio_reference(audio or [])
    song_peak = max(sm, default=0.0)
    secs = [to_seconds(b) for b in bars]
    marks = {round(b, 6) for b in boundaries}
    phrase = {round(b, 6) for b in bars[::8]}
    last = len(bars) - 1
    scored: dict[tuple[int, int], Suggestion | None] = {}

    def evaluate(a: int, z: int) -> Suggestion | None:
        key = (a, z)
        if key in scored:
            return scored[key]
        out = None
        start_s, end_s = secs[a], secs[z]
        target = _target_of(end_s - start_s)
        i0, i1 = round(start_s), min(len(raw), round(end_s))
        if (
            target is not None
            and start_s < duration_s
            and end_s <= duration_s + 1e-6
            and i1 - i0 >= 2
        ):
            ends = (round(bars[a], 6), round(bars[z], 6))
            aligned = sum(1.0 if e in marks else 0.5 if e in phrase else 0.0 for e in ends) / 2
            valley = (
                cut_valley(note_pre, audio_pre, audio_ref, start_s)
                + cut_valley(note_pre, audio_pre, audio_ref, end_s)
            ) / 2
            parts, peak_i = score_window(
                sm, sm_pre, raw, pres, song_peak, i0, i1, target, aligned, valley
            )
            reason = _reason(sm, i0, i1, peak_i, start_s, end_s)
            points = round(sum(p.points for p in parts), 1)
            out = Suggestion(bars[a], bars[z], start_s, end_s, target, points, reason, tuple(parts))
        scored[key] = out
        return out

    def rank(a: int, z: int) -> tuple[float, int, int]:
        got = scored[(a, z)]
        return (-(got.score if got else -1.0), a, z)

    for a in range(0, last, SEED_STEP):
        for z in range(a + SEED_STEP, last + 1, SEED_STEP):
            if secs[z] - secs[a] > max(t + TOLERANCE_S[t] for t in TARGETS):
                break
            evaluate(a, z)
    for _ in range(MAX_PASSES):
        top = sorted((k for k, v in scored.items() if v is not None), key=lambda k: rank(*k))
        before = [rank(*k) for k in top[:SEED_KEEP]]
        for a, z in top[:SEED_KEEP]:
            for step in MOVES:
                for na, nz in ((a - step, z), (a + step, z), (a, z - step), (a, z + step)):
                    if 0 <= na < nz <= last:
                        evaluate(na, nz)
        top = sorted((k for k, v in scored.items() if v is not None), key=lambda k: rank(*k))
        if [rank(*k) for k in top[:SEED_KEEP]] == before:
            break  # no pass improved the best windows
    found = sorted(
        (v for v in scored.values() if v is not None), key=lambda v: (-v.score, v.start_s, v.end_s)
    )
    picks: list[Suggestion] = []
    for cand in found:
        if cand.score < MIN_POINTS:
            break
        if all(_overlap(cand, p) < MAX_OVERLAP for p in picks):
            picks.append(cand)
            if len(picks) == COUNT:
                break
    return picks
