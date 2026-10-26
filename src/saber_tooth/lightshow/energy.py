import math

from saber_tooth.analysis import Analysis, onset_density
from saber_tooth.lightshow.units import BAR
from saber_tooth.model import Beatmap
from saber_tooth.timing import Timing


def last_note_beat(beatmap: Beatmap) -> float:
    return max((n.beat for d in beatmap.difficulties.values() for n in d.notes), default=0.0)


def bar_count(beatmap: Beatmap) -> int:
    return int(last_note_beat(beatmap) // BAR) + 1


def _p90_normalise(values: list[float]) -> list[float]:
    if not values:
        return values
    s = sorted(values)
    top = s[min(len(s) - 1, math.ceil(0.9 * len(s)) - 1)]
    if top <= 0:
        return [0.0] * len(values)
    return [min(1.0, max(0.0, v / top)) for v in values]


def bar_energy(beatmap: Beatmap, timing: Timing, analysis: Analysis | None) -> list[float]:
    """Energy in [0, 1] per 4-beat bar: audio onsets if analysed, else note density."""
    n_bars = bar_count(beatmap)
    if analysis is not None:
        raw = [
            onset_density(analysis, timing.to_seconds(i * BAR), timing.to_seconds((i + 1) * BAR))
            for i in range(n_bars)
        ]
    else:
        densest = max(beatmap.difficulties.values(), key=lambda d: len(d.notes), default=None)
        counts = [0.0] * n_bars
        for n in densest.notes if densest else []:
            counts[int(n.beat // BAR)] += 1
        raw = counts
    return _p90_normalise(raw)
