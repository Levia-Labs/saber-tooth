"""Auto crop: rank 1 and 2 minute windows by how good they are to play and keep the best three.

Windows start and end on bar lines. A window is scored on the smoothed notes-per-second curve of
the hardest difficulty (peak, rise, release, quiet cut points), on every difficulty's mean density
(comfort), on empty gaps, on variety and on how close it is to its target length. Pure and
deterministic: the same inputs give the same list.
"""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import accumulate

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
WEIGHTS = {
    "peak": 0.25,  # window peak against the song peak
    "arc": 0.20,  # rise before and release after the peak (the weaker of the two)
    "position": 0.10,  # the peak in the middle zone, not at an edge
    "comfort": 0.10,  # mean NPS in a playable range on every difficulty
    "gaps": 0.10,  # no long empty stretch
    "variety": 0.10,  # the energy changes from block to block
    "cut": 0.10,  # quiet entry and exit, cuts on section or phrase lines
    "length": 0.05,  # close to the target length
}


@dataclass(frozen=True)
class Suggestion:
    start_beat: float
    end_beat: float
    start_s: float
    end_s: float
    target_s: int
    score: float
    reason: str

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
) -> tuple[float, int]:
    """Return (score in [0, 1], bin of the window peak) for the bins [i0, i1)."""
    n = i1 - i0
    peak_i = max(range(i0, i1), key=lambda i: (sm[i], -i))
    top = sm[peak_i]
    if top <= 0 or song_peak <= 0:
        return 0.0, peak_i
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
    }
    return sum(WEIGHTS[k] * v for k, v in parts.items()), peak_i


def _overlap(a: Suggestion, b: Suggestion) -> float:
    shared = min(a.end_s, b.end_s) - max(a.start_s, b.start_s)
    return max(0.0, shared) / min(a.length_s, b.length_s)


def suggest_crops(
    series: dict[str, list[float]],
    hardest: str,
    bars: list[float],
    to_seconds: Callable[[float], float],
    boundaries: list[float],
    duration_s: float,
) -> list[Suggestion]:
    """The best distinct windows (at most COUNT), best first. `bars` are bar-line beats."""
    raw = series.get(hardest, [])
    if not raw or len(bars) < 2:
        return []
    sm = _smooth(raw)
    sm_pre = [0.0, *accumulate(sm)]
    pres = [[0.0, *accumulate(s)] for s in series.values()]
    song_peak = max(sm, default=0.0)
    secs = [to_seconds(b) for b in bars]
    marks = {round(b, 6) for b in boundaries}
    phrase = {round(b, 6) for b in bars[::8]}
    found: list[Suggestion] = []
    for a, start_s in enumerate(secs):
        if start_s >= duration_s:
            break
        for target in TARGETS:
            tol = TOLERANCE_S[target]
            for z in range(a + 1, len(bars)):
                end_s = secs[z]
                if end_s - start_s > target + tol:
                    break
                if end_s - start_s < target - tol or end_s > duration_s + 1e-6:
                    continue
                i0, i1 = round(start_s), min(len(raw), round(end_s))
                if i1 - i0 < 2:
                    continue
                ends = (round(bars[a], 6), round(bars[z], 6))
                aligned = sum(1.0 if e in marks else 0.5 if e in phrase else 0.0 for e in ends) / 2
                score, peak_i = score_window(
                    sm, sm_pre, raw, pres, song_peak, i0, i1, target, aligned
                )
                reason = _reason(sm, i0, i1, peak_i, start_s, end_s)
                found.append(
                    Suggestion(bars[a], bars[z], start_s, end_s, target, round(score, 4), reason)
                )
    found.sort(key=lambda s: (-s.score, s.start_s, s.end_s))
    picks: list[Suggestion] = []
    for cand in found:
        if all(_overlap(cand, p) < MAX_OVERLAP for p in picks):
            picks.append(cand)
            if len(picks) == COUNT:
                break
    return picks
