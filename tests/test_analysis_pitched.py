import json
from pathlib import Path

from saber_tooth.analysis import Analysis, read_project

SONG1 = Path(__file__).parent / "fixtures" / "analyser" / "song1"


def test_pitched_tracks_are_read_in_time_order(tmp_path):
    (tmp_path / "meta.json").write_text(
        json.dumps({"name": "p", "key": "C", "bpm": 120}), encoding="utf-8"
    )
    (tmp_path / "bass.csv").write_text("1.0,3\n0.5,4\n", encoding="utf-8")
    (tmp_path / "chords.csv").write_text("2.0,1\n", encoding="utf-8")
    (tmp_path / "melody.csv").write_text("3.0,60\n1.0,55\n2.0,x\n", encoding="utf-8")
    a = read_project(tmp_path)
    assert a.bass == [0.5, 1.0] and a.chords == [2.0]
    assert a.melody == [1.0, 2.0, 3.0] and a.melody_ids == [55, 0, 60]


def test_missing_or_empty_pitched_files_give_empty_lists():
    a = read_project(SONG1)
    assert a.bass == [] and a.chords == [] and a.melody == [] and a.melody_ids == []


def test_existing_positional_construction_still_works():
    a = Analysis("x", "k", 120.0, [], [0.0], [], [], None)
    assert a.bass == [] and a.melody_ids == []
