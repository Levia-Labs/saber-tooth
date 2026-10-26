from saber_tooth.analysis import Analysis
from saber_tooth.model import BpmEvent

CHANGE_RATIO = 0.005
MIN_INTERVAL_S = 1e-3


def tempo_map(a: Analysis) -> tuple[float, list[BpmEvent]]:
    """Base bpm and events so that map beat `phase + k` lands on `a.beats[k]`.

    `phase` is `a.beats[0] * base / 60`; an event is emitted only where the local bpm differs
    from the current one by more than 0.5 percent.
    """
    beats = a.beats
    if len(beats) < 2:
        return a.bpm, []
    local = [60.0 / max(beats[k + 1] - beats[k], MIN_INTERVAL_S) for k in range(len(beats) - 1)]
    local.append(local[-1])
    base = local[0]
    phase = beats[0] * base / 60.0
    events: list[BpmEvent] = []
    current = base
    for k in range(1, len(local)):
        if abs(local[k] - current) / current > CHANGE_RATIO:
            events.append(BpmEvent(phase + k, local[k]))
            current = local[k]
    return base, events
