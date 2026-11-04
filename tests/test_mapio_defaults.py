"""Beat Saber omits zero-valued fields in v3 and v4 files; the readers must read them as 0."""

from saber_tooth.mapio.read_v3 import read_v3
from saber_tooth.mapio.read_v4 import read_v4


def test_v3_missing_fields_default_to_zero():
    data = {
        "colorNotes": [{"b": 2, "c": 1, "x": 2, "d": 1}, {"b": 3, "x": 1, "d": 1}, {"b": 9}],
        "obstacles": [{"b": 4, "x": 1, "d": 2, "w": 1, "h": 5}, {"b": 6}],
        "bombNotes": [{"b": 5}],
        "basicBeatmapEvents": [{"b": 1}],
        "bpmEvents": [{"m": 120}],
    }
    d = read_v3(data, "Easy", 10.0, 0.0, "EasyStandard.dat")
    assert [(n.beat, n.x, n.y, int(n.color)) for n in d.notes] == [
        (2.0, 2, 0, 1),
        (3.0, 1, 0, 0),
        (9.0, 0, 0, 0),
    ]
    assert len(d.walls) == 2 and len(d.bombs) == 1 and len(d.events) == 1
    assert d.bpm_events[0].beat == 0.0


def test_v4_missing_index_and_beat_default_to_zero():
    data = {
        "colorNotes": [{"b": 10.0}, {"b": 10.5, "i": 1}],
        "colorNotesData": [{"x": 1, "d": 1}, {"c": 1, "x": 2, "y": 1, "d": 6}],
        "obstacles": [{"b": 3}],
        "obstaclesData": [{"x": 1, "d": 2, "w": 1, "h": 3}],
    }
    d = read_v4(data, None, "Easy", 10.0, 0.0, "Easy.beatmap.dat")
    assert [(n.beat, n.x, n.y, int(n.color)) for n in d.notes] == [
        (10.0, 1, 0, 0),
        (10.5, 2, 1, 1),
    ]
    assert len(d.walls) == 1
