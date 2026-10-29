import threading
import time

import httpx
import pytest

from saber_tooth.analyser_client import AnalyserClient, AnalyserError
from saber_tooth.jobs import JobCancelled
from saber_tooth.service import Service, map_id_for
from saber_tooth.store import Store
from tests.test_service import NAME, _build_levels, _fake_encode
from tests.test_service_generate import _project


class Progress:
    """Records progress texts; `check()` raises once `stop` is set, like a cancelled job."""

    def __init__(self) -> None:
        self.texts: list[str] = []
        self.stop = threading.Event()

    def check(self) -> None:
        if self.stop.is_set():
            raise JobCancelled

    def __call__(self, text: str) -> None:
        self.check()
        self.texts.append(text)


def _svc(tmp_path, handler, **client_kw) -> Service:
    _project(tmp_path / "up")  # the analyser's project folder for the fake response
    levels, data = tmp_path / "levels", tmp_path / "data"
    levels.mkdir()
    data.mkdir()
    _build_levels(levels)
    client = AnalyserClient(
        "http://analyser", tmp_path / "up", httpx.MockTransport(handler), **client_kw
    )
    svc = Service(levels, data, Store(data / "s.db"), client, _fake_encode)
    svc.refresh_library()
    return svc


def _ok(calls: list):
    def handler(request):
        calls.append(request.url.path)
        headers = {"Content-Disposition": 'attachment; filename="song1_tracks.zip"'}
        return httpx.Response(200, content=b"zip", headers=headers)

    return handler


def test_scan_reports_each_stage_in_order(tmp_path):
    svc = _svc(tmp_path, _ok([]))
    p = Progress()
    svc.run_scan(map_id_for(NAME), p)
    wanted = ["decoding audio", "analysing beats", "checking rules"]
    stages = [t for t in p.texts if t in wanted]
    assert stages == wanted


def test_cancel_while_the_analyser_is_busy_ends_the_scan_within_a_second(tmp_path):
    release = threading.Event()

    def slow(request):
        release.wait(10)
        return httpx.Response(500)

    svc = _svc(tmp_path, slow)
    p = Progress()
    threading.Timer(0.3, p.stop.set).start()
    started = time.monotonic()
    try:
        with pytest.raises(JobCancelled):
            svc.run_scan(map_id_for(NAME), p)
        assert time.monotonic() - started < 1.5
    finally:
        release.set()


def test_the_analyser_wait_has_a_hard_stage_timeout_with_a_clear_error(tmp_path):
    release = threading.Event()

    def slow(request):
        release.wait(10)
        return httpx.Response(500)

    client = AnalyserClient(
        "http://analyser", tmp_path, httpx.MockTransport(slow), stage_timeout=0.4
    )
    song = tmp_path / "song.ogg"
    song.write_bytes(b"x")
    try:
        with pytest.raises(AnalyserError, match="did not answer within"):
            client.analyse_file(song, "song.ogg")
    finally:
        release.set()


def test_the_same_audio_is_analysed_once_for_scan_and_fix(tmp_path):
    calls: list = []
    svc = _svc(tmp_path, _ok(calls))
    mid = map_id_for(NAME)
    svc.run_scan(mid)
    svc.run_scan(mid)
    assert calls == ["/upload"]


def test_changed_audio_is_analysed_again(tmp_path):
    calls: list = []
    svc = _svc(tmp_path, _ok(calls))
    mid = map_id_for(NAME)
    svc.run_scan(mid)
    (svc.levels / NAME / "song.ogg").write_bytes(b"different audio")
    svc.run_scan(mid)
    assert calls == ["/upload", "/upload"]


def test_a_scan_stops_proposing_at_its_time_budget_and_still_stores_every_finding(
    tmp_path, monkeypatch
):
    from saber_tooth.service import scan

    svc = _svc(tmp_path, _ok([]))
    mid = map_id_for(NAME)
    monkeypatch.setattr(scan, "PROPOSE_BUDGET_S", -1.0)
    p = Progress()
    out = svc.run_scan(mid, p)
    findings = svc.store.scan_info(mid)["findings"]
    assert out["proposals"] == 0 and out["unproposed"] == len(findings) > 0
    assert any("time budget reached" in t for t in p.texts)
