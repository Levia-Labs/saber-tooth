from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.model import BpmEvent
from saber_tooth.timing import Timing


def test_constant_bpm():
    t = Timing(120.0, [])
    assert t.to_seconds(4.0) == 2.0
    assert t.to_beats(2.0) == 4.0


def test_timing_with_bpm_change():
    t = Timing(120.0, [BpmEvent(beat=4.0, bpm=60.0)])
    assert t.to_seconds(4.0) == 2.0
    assert t.to_seconds(5.0) == 3.0
    assert t.to_beats(3.0) == 5.0


@given(st.floats(min_value=0, max_value=2000), st.floats(min_value=40, max_value=400))
def test_round_trip(beat, bpm):
    t = Timing(bpm, [BpmEvent(beat=16.0, bpm=bpm * 1.5)])
    assert abs(t.to_beats(t.to_seconds(beat)) - beat) < 1e-6
