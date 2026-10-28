# ruff: noqa: F811
import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.checks.structure import missing_difficulty
from saber_tooth.mapio import load_map
from saber_tooth.model import BpmEvent
from saber_tooth.service import map_id_for
from saber_tooth.timing import Timing
from tests.crop_helpers import NAME, cuts, make_service, stepped_map  # noqa: F401
from tests.test_api import _wait
from tests.test_service import _hashes

MID = map_id_for(NAME)
BANDS = {"60": ("1 min", 54.0, 66.0), "120": ("2 min", 108.0, 132.0)}


def _crop(http, key):
    """Read the timeline, crop its best window, return (window, finished job result)."""
    window = http.get(f"/api/maps/{MID}/timeline").json()["lengths"][key]["suggestions"][0]
    body = {"start_beat": window["start_beat"], "end_beat": window["end_beat"]}
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=body).json()["job"])
    assert job["status"] == "done", job
    return window, job["result"]


def _assert_fits_the_audio(written, cut):
    """Every note lies inside the cut audio, and none before the 2 s lead-in."""
    _src, _dst, _start_s, length_s, lead_s, fade_in_s, fade_out_s = cut
    assert fade_in_s == 0.5 and fade_out_s > 0
    for d in written.difficulties.values():
        timing = Timing(written.info.bpm, d.bpm_events)
        times = [timing.to_seconds(n.beat) for n in d.notes]
        assert all(t <= lead_s + length_s + 1e-6 for t in times)
        assert not times or min(times) >= 2.0 - 1e-6


@pytest.mark.parametrize("key", ["60", "120"])
def test_timeline_then_crop_then_read_back(tmp_path, cuts, key):
    label, lo, hi = BANDS[key]
    svc = make_service(tmp_path)
    original = svc.levels / NAME
    before = _hashes(original)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        window, result = _crop(http, key)
    assert lo <= window["length_s"] <= hi
    assert result["folder"] == f"{NAME} [{label}]"
    written = load_map(svc.levels / result["folder"])
    assert missing_difficulty(written) == []
    assert written.info.song_name == f"Song [{label}]"
    assert len(cuts) == 1 and cuts[0][3] == pytest.approx(window["length_s"])
    _assert_fits_the_audio(written, cuts[0])
    assert _hashes(original) == before


def test_a_map_with_a_tempo_change_crops_to_a_consistent_folder(tmp_path, cuts):
    bm = stepped_map(72)
    for d in bm.difficulties.values():
        d.bpm_events = [BpmEvent(100.0, 100.0)]
    svc = make_service(tmp_path, bm)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        window, result = _crop(http, "60")
    assert 54.0 <= window["length_s"] <= 66.0  # measured in seconds across the tempo change
    written = load_map(svc.levels / result["folder"])
    assert missing_difficulty(written) == []
    assert written.info.bpm == 120.0  # the tempo at the cut
    # the change at beat 100 is inside the window: kept, moved by the 4-beat lead-in
    assert written.difficulties["Expert"].bpm_events == [BpmEvent(104.0, 100.0)]
    _assert_fits_the_audio(written, cuts[0])


def test_cropping_twice_never_overwrites(tmp_path, cuts):
    svc = make_service(tmp_path)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        _, first = _crop(http, "60")
        _, second = _crop(http, "60")
    assert (first["folder"], second["folder"]) == ("Song [1 min]", "Song [1 min 2]")
    assert len(cuts) == 2
