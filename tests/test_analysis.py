from pathlib import Path

from saber_tooth.analysis import Analysis, onset_density, read_project

FIX = Path(__file__).parent / "fixtures" / "analyser" / "song1"


def test_read_project():
    a = read_project(FIX)
    assert a.name == "song1" and a.key == "A minor"
    assert a.bpm == 120.0 and a.kick and a.audio is None
    assert a.snare[0] == 0.5 and len(a.beats) == 8


def test_missing_csv_is_empty(tmp_path):
    (tmp_path / "meta.json").write_text('{"name":"n","key":"k","bpm":90}', encoding="utf-8")
    (tmp_path / "audio.wav").write_bytes(b"")
    a = read_project(tmp_path)
    assert a.kick == [] and a.hh == [] and a.audio == tmp_path / "audio.wav"


def test_onset_density_weighted():
    a = Analysis("x", "k", 120.0, [], [0.0, 1.0], [0.5], [0.2], None)
    assert onset_density(a, 0.0, 2.0) == (2 * 1.0 + 0.8 + 0.3) / 2.0
    assert onset_density(a, 1.0, 1.0) == 0.0
