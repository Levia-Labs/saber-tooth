import json
import shutil
from pathlib import Path

import pytest

from saber_tooth.mapio import MapParseError, load_map, write_map
from saber_tooth.mapio.tempo_regions import V2_KEYS, V4_KEYS, merge_events, regions_to_events
from saber_tooth.model import BpmEvent
from saber_tooth.timing import Timing

FIX = Path(__file__).parent / "fixtures" / "maps"


def _v4(si_ei_sb_eb, freq=44100):
    return {
        "songFrequency": freq,
        "bpmData": [dict(zip(("si", "ei", "sb", "eb"), r, strict=True)) for r in si_ei_sb_eb],
    }


def test_region_math_and_dedup():
    data = _v4([(0, 88200, 0, 4), (88200, 176400, 4, 10), (176400, 264600, 10, 16)])
    events = regions_to_events(data, V4_KEYS)
    assert events == [BpmEvent(0.0, 120.0), BpmEvent(4.0, 180.0), BpmEvent(10.0, 180.0)]
    assert merge_events([], events, 120.0) == [BpmEvent(4.0, 180.0)]


def test_v2_regions_keys():
    data = {
        "_songFrequency": 48000,
        "_regions": [
            {"_startSampleIndex": 0, "_endSampleIndex": 48000, "_startBeat": 0, "_endBeat": 3}
        ],
    }
    assert regions_to_events(data, V2_KEYS) == [BpmEvent(0.0, 180.0)]


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"songFrequency": 0, "bpmData": []},
        {"songFrequency": 44100, "bpmData": [1]},
        _v4([(10, 5, 0, 1)]),
        _v4([(0, 10, 0, "x")]),
    ],
)
def test_malformed_regions(data):
    with pytest.raises(MapParseError):
        regions_to_events(data, V4_KEYS)


def test_v4_map_timing_after_change():
    m = load_map(FIX / "v4_audio_bpm")
    d = m.difficulties["Easy"]
    assert d.bpm_events == [BpmEvent(4.0, 180.0), BpmEvent(10.0, 240.0)]
    assert Timing(m.info.bpm, d.bpm_events).to_seconds(d.notes[0].beat) == pytest.approx(2 + 2 / 3)


def test_missing_audio_data_is_not_an_error(tmp_path):
    shutil.copytree(FIX / "v4_audio_bpm", tmp_path / "m")
    (tmp_path / "m" / "AudioData.dat").unlink()
    assert load_map(tmp_path / "m").difficulties["Easy"].bpm_events == []


def test_malformed_audio_data(tmp_path):
    shutil.copytree(FIX / "v4_audio_bpm", tmp_path / "m")
    (tmp_path / "m" / "AudioData.dat").write_text(
        '{"songFrequency": 1, "bpmData": 3}', encoding="utf-8"
    )
    with pytest.raises(MapParseError):
        load_map(tmp_path / "m")


def test_unsafe_audio_data_name(tmp_path):
    shutil.copytree(FIX / "v4_audio_bpm", tmp_path / "m")
    info = tmp_path / "m" / "Info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace("AudioData.dat", "../x.dat"), encoding="utf-8"
    )
    with pytest.raises(MapParseError):
        load_map(tmp_path / "m")


def test_bpminfo_next_to_v2_map(tmp_path):
    shutil.copytree(FIX / "v2_basic", tmp_path / "m")
    region = {"_startSampleIndex": 0, "_endSampleIndex": 44100, "_startBeat": 0, "_endBeat": 3}
    (tmp_path / "m" / "BPMInfo.dat").write_text(
        json.dumps({"_songFrequency": 44100, "_regions": [region]}),
        encoding="utf-8",
    )
    assert load_map(tmp_path / "m").difficulties["Hard"].bpm_events == [BpmEvent(0.0, 180.0)]


def test_round_trip_writes_bpm_events(tmp_path):
    write_map(load_map(FIX / "v4_audio_bpm"), tmp_path / "out", FIX / "v4_audio_bpm")
    data = json.loads((tmp_path / "out" / "Easy.dat").read_text(encoding="utf-8"))
    assert data["bpmEvents"] == [{"b": 4.0, "m": 180.0}, {"b": 10.0, "m": 240.0}]


def _timing(data, bpm=120.0, own=()):
    ev = merge_events(list(own), regions_to_events(data, V4_KEYS), bpm)
    return Timing(bpm, ev)


def test_zero_length_region_skipped():
    data = _v4([(0, 44100, 0, 2), (44100, 44100, 2, 2), (44100, 88200, 2, 6)])
    assert regions_to_events(data, V4_KEYS) == [BpmEvent(0.0, 120.0), BpmEvent(2.0, 240.0)]


def test_lead_in_with_beat_prepends_segment():
    data = _v4([(44100, 88200, 1, 3)])
    t = _timing(data)
    assert t.to_seconds(1.0) == pytest.approx(1.0)
    assert t.to_seconds(3.0) == pytest.approx(2.0)
    assert t.to_seconds(0.5) == pytest.approx(0.5)


def test_pure_lead_in_unsupported():
    with pytest.raises(MapParseError, match="lead-in"):
        regions_to_events(_v4([(44100, 88200, 0, 2)]), V4_KEYS)


def test_beat_gap_is_filled():
    data = _v4([(0, 44100, 0, 2), (88200, 132300, 6, 8)])
    t = _timing(data)
    assert t.to_seconds(6.0) == pytest.approx(2.0)
    assert t.to_seconds(4.0) == pytest.approx(1.5)
    assert t.to_seconds(8.0) == pytest.approx(3.0)


def test_one_sample_gap_is_ignored():
    data = _v4([(0, 44100, 0, 2), (44101, 88200, 2, 4)])
    assert [e.beat for e in regions_to_events(data, V4_KEYS)] == [0.0, 2.0]


@pytest.mark.parametrize(
    "rows",
    [
        [(0, 88200, 0, 4), (44100, 132300, 4, 8)],
        [(0, 88200, 0, 4), (88200, 132300, 3, 8)],
        [(0, 44100, 0, 2), (88200, 132300, 2, 4)],
    ],
)
def test_unsupported_layouts(rows):
    with pytest.raises(MapParseError, match="unsupported tempo layout"):
        regions_to_events(_v4(rows), V4_KEYS)


def test_own_event_wins_and_later_equal_region_kept():
    data = _v4([(0, 44100, 0, 2), (44100, 88200, 2, 4), (88200, 132300, 4, 8)])
    own = [BpmEvent(2.0, 90.0)]
    merged = merge_events(own, regions_to_events(data, V4_KEYS), 120.0)
    assert merged == [BpmEvent(2.0, 90.0), BpmEvent(4.0, 240.0)]


def test_v2_own_events_beat_bpminfo(tmp_path):
    shutil.copytree(FIX / "v2_bpm", tmp_path / "m")
    own = load_map(tmp_path / "m")
    region = {"_startSampleIndex": 0, "_endSampleIndex": 44100, "_startBeat": 0, "_endBeat": 9}
    (tmp_path / "m" / "BPMInfo.dat").write_text(
        json.dumps({"_songFrequency": 44100, "_regions": [region]}), encoding="utf-8"
    )
    again = load_map(tmp_path / "m")
    for name, d in own.difficulties.items():
        assert again.difficulties[name].bpm_events == d.bpm_events
