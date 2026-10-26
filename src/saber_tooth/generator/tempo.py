import statistics

from saber_tooth.analysis import Analysis
from saber_tooth.model import BpmEvent

CHANGE_RATIO = 0.005
MAX_DRIFT_S = 0.010
MIN_INTERVAL_S = 1e-3
BASE_WINDOW = 8


def tempo_map(a: Analysis) -> tuple[float, list[BpmEvent]]:
    """Base bpm and events so that map beat `phase + k` lands on `a.beats[k]`.

    `phase` is `a.beats[0] * base / 60`. The projected time of every grid beat under the tempo
    map built so far is tracked; an event is emitted at beat k when the local bpm differs from
    the current one by more than 0.5 percent or when the next beat would land more than 10 ms
    off. The new bpm is chosen so the next beat lands exactly, which also removes any drift.
    """
    beats = a.beats
    if len(beats) < 2:
        return a.bpm, []
    gaps = [max(beats[k + 1] - beats[k], MIN_INTERVAL_S) for k in range(len(beats) - 1)]
    base = 60.0 / statistics.median(gaps[:BASE_WINDOW])
    phase = beats[0] * base / 60.0
    events: list[BpmEvent] = []
    current, seg_k, seg_time = base, 0, beats[0]
    for k in range(1, len(gaps)):  # the last beat has no following interval to steer
        here = seg_time + (k - seg_k) * 60.0 / current
        local = 60.0 / gaps[k]
        steer = abs(local - current) / current > CHANGE_RATIO
        steer = steer or abs(here + 60.0 / current - beats[k + 1]) > MAX_DRIFT_S
        if steer:
            current = 60.0 / max(beats[k + 1] - here, MIN_INTERVAL_S)
            seg_k, seg_time = k, here
            events.append(BpmEvent(phase + k, current))
    return base, events
