from saber_tooth.analysis import Analysis
from saber_tooth.generator import tempo_map
from saber_tooth.timing import Timing


def _max_error(beats: list[float]) -> tuple[float, int]:
    bpm, events = tempo_map(Analysis("s", "A", 120, beats, [], [], [], None))
    timing = Timing(bpm, events)
    phase = beats[0] * bpm / 60.0
    errors = [abs(timing.to_seconds(phase + k) - b) for k, b in enumerate(beats)]
    return max(errors), len(events)


def test_noisy_first_interval_lands_within_10ms():
    beats = [1.0, 1.54] + [1.54 + 0.5 * i for i in range(1, 60)]
    error, events = _max_error(beats)
    assert error <= 0.010
    assert events <= 2


def test_steady_first_interval_adds_no_first_beat_event():
    beats = [1.0 + 0.5 * i for i in range(60)]
    assert _max_error(beats)[1] == 0
