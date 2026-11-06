"""Analyser client retry and concurrency; Fix needs analysis, scan flags its absence."""

import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from saber_tooth.analyser_client import AnalyserClient, AnalyserError
from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from saber_tooth.service.background import _rescan_job
from saber_tooth.service.errors import AnalysisUnavailable
from saber_tooth.service.fixsave import replace_reasons
from tests.test_analyser_client import _project, _zip_response
from tests.test_api import MID, NAME, _wait
from tests.test_service import _make, _up, down


def _client(tmp_path, handler, **kw):
    return AnalyserClient("http://analyser", tmp_path, httpx.MockTransport(handler), **kw)


def _wav(tmp_path):
    wav = tmp_path / "in.wav"
    wav.write_bytes(b"RIFF")
    return wav


def test_transient_failures_are_retried_then_succeed(tmp_path):
    _project(tmp_path)
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("reset")
        if len(calls) == 2:
            return httpx.Response(503, json={"error": "busy"})
        return _zip_response("song")

    result = _client(tmp_path, handler, backoff=0.0).analyse_file(_wav(tmp_path), "a.ogg")
    assert result.name == "song" and len(calls) == 3


def test_slot_locks_live_in_the_lock_dir_not_the_read_only_uploads(tmp_path):
    # The compose file mounts the uploads volume read-only, so locks there fail every analysis.
    _project(tmp_path)
    locks = tmp_path / "data" / "analyser-slots"
    client = _client(tmp_path, lambda r: _zip_response("song"), lock_dir=locks)
    client.analyse_file(_wav(tmp_path), "a.ogg")
    assert any(locks.iterdir()) and not (tmp_path / ".slots").exists()


def test_a_refusal_is_not_retried_and_exhausted_retries_raise(tmp_path):
    calls = []

    def refuse(request):
        calls.append(1)
        return httpx.Response(400, json={"error": "bad audio"})

    with pytest.raises(AnalyserError, match="bad audio"):
        _client(tmp_path, refuse, backoff=0.0).analyse_file(_wav(tmp_path), "a.ogg")
    assert len(calls) == 1
    calls.clear()

    def reset(request):
        calls.append(1)
        raise httpx.ConnectError("reset")

    with pytest.raises(AnalyserError, match="unreachable"):
        _client(tmp_path, reset, backoff=0.0, attempts=3).analyse_file(_wav(tmp_path), "a.ogg")
    assert len(calls) == 3


@pytest.mark.parametrize("slots", [1, 2])
def test_in_flight_analyses_never_exceed_the_slots(tmp_path, slots):
    _project(tmp_path)
    lock, state = threading.Lock(), {"now": 0, "max": 0}

    def handler(request):
        with lock:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        time.sleep(0.15)
        with lock:
            state["now"] -= 1
        return _zip_response("song")

    client = _client(tmp_path, handler, slots=slots)
    wav = _wav(tmp_path)
    threads = [threading.Thread(target=client.analyse_file, args=(wav, "a.ogg")) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert state["max"] == slots


def test_fix_fails_without_analysis_and_writes_no_copy(tmp_path):
    svc = _make(tmp_path, handler=down)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        job = _wait(http, http.post(f"/api/maps/{MID}/fix").json()["job"])
    assert job["status"] == "failed"
    assert "audio analysis unavailable" in job["error"] and "unreachable" in job["error"]
    assert not (svc.levels / f"{NAME} [saber-tooth]").exists()
    with pytest.raises(AnalysisUnavailable):
        svc.fix_map(MID)


def test_scan_without_analysis_is_flagged_and_rescanned_once_it_answers(tmp_path):
    svc = _make(tmp_path, handler=down)
    result = svc.run_scan(MID)
    assert result["analysis"] is False and result["unanalysed"] is True
    assert svc.store.scan_info(MID)["unanalysed"] is True
    assert svc.store.unanalysed_ids() == [MID]
    svc.client = AnalyserClient(
        "http://analyser", tmp_path / "up", httpx.MockTransport(_up(tmp_path))
    )
    _rescan_job(svc)
    assert svc.store.scan_info(MID)["unanalysed"] is False
    assert svc.store.unanalysed_ids() == []


def test_a_new_runs_reasons_replace_the_stored_ones(tmp_path):
    svc = _make(tmp_path)
    mid = map_id_for(NAME)
    finding = {"rule": "r", "difficulty": "Hard", "beat_start": 1.0, "beat_end": 2.0}
    old = {**finding, "unfixed_reason": "no verified fix", "message": "m"}
    other = {"rule": "q", "difficulty": "Hard", "beat_start": 3.0, "beat_end": 4.0, "message": "n"}
    svc.store.replace_open_proposals(mid, [], {"findings": [old, other], "analysis": None})
    fresh = [{**other, "reason": "needs a gap"}]
    replace_reasons(svc.store, mid, fresh)
    found = {f["rule"]: f.get("unfixed_reason") for f in svc.store.scan_info(mid)["findings"]}
    assert found == {"r": None, "q": "needs a gap"}
