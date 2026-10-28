"""Notes per second series of a map: 1 s bins, bombs and arcs excluded, a chain counted once."""

import math

from saber_tooth.model import DIFFICULTIES, Beatmap, Difficulty
from saber_tooth.timing import Timing


def note_beats(d: Difficulty) -> list[float]:
    """Ascending beats of every note; a chain adds its head once, arcs add none."""
    heads = {(round(n.beat, 6), n.x, n.y, int(n.color)) for n in d.notes}
    beats = [n.beat for n in d.notes]
    for chain in d.raw.get("burstSliders", []):
        try:
            key = (round(float(chain["b"]), 6), int(chain["x"]), int(chain["y"]), int(chain["c"]))
        except (KeyError, TypeError, ValueError):
            continue
        if key not in heads:
            heads.add(key)
            beats.append(key[0])
    return sorted(beats)


def nps_series(d: Difficulty, timing: Timing, duration_s: float) -> list[float]:
    """Notes per 1 s bin; notes after the song end are dropped."""
    series = [0.0] * max(1, math.ceil(duration_s))
    for beat in note_beats(d):
        i = int(timing.to_seconds(beat))
        if 0 <= i < len(series):
            series[i] += 1.0
    return series


def all_series(beatmap: Beatmap, timing: Timing, duration_s: float) -> dict[str, list[float]]:
    """The series of every difficulty that has notes, in difficulty order."""
    out = {}
    for name in DIFFICULTIES:
        d = beatmap.difficulties.get(name)
        if d is not None and d.notes:
            out[name] = nps_series(d, timing, duration_s)
    return out


def peak(series: list[float]) -> float:
    return max(series, default=0.0)


def mean_nps(series: list[float], start_s: float, end_s: float) -> float:
    """Mean over [start_s, end_s], weighting partial bins by their overlap."""
    if end_s <= start_s:
        return 0.0
    total = 0.0
    for i, v in enumerate(series):
        overlap = min(end_s, i + 1.0) - max(start_s, float(i))
        if overlap > 0:
            total += v * overlap
    return total / (end_s - start_s)


def slope(series: list[float], start_s: float, end_s: float) -> float:
    """Least squares trend of the bins whose centre lies in [start_s, end_s); 0 under two bins."""
    lo = max(0, math.ceil(start_s - 0.5))
    hi = min(len(series), math.ceil(end_s - 0.5))
    ys = series[lo:hi]
    n = len(ys)
    if n < 2:
        return 0.0
    mx, my = (n - 1) / 2, sum(ys) / n
    den = sum((x - mx) ** 2 for x in range(n))
    return sum((x - mx) * (y - my) for x, y in enumerate(ys)) / den
