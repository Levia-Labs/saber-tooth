"""Startup and listing: re-index and copy-scan backfill stay off the request thread."""

import shutil
import threading
import time

from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import background, map_id_for
from tests.test_service import NAME, _make


def _wait(cond, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_list_does_not_wait_for_a_reindex(tmp_path):
    svc = _make(tmp_path)  # the store now holds an index
    gate, started = threading.Event(), threading.Event()
    real = svc._reindex

    def slow():
        started.set()
        gate.wait(10)
        return real()

    svc._reindex = slow
    (svc.levels / "Other").mkdir()  # listing changed: a re-index is due
    try:
        with TestClient(create_app(svc), base_url="http://localhost") as http:
            t0 = time.perf_counter()
            resp = http.get("/api/maps")
            elapsed = time.perf_counter() - t0
            assert resp.status_code == 200 and resp.json()["total"] >= 1
            assert started.wait(5) and elapsed < 1.0
    finally:
        gate.set()
    assert _wait(lambda: not svc._reindexing)


def test_backfill_scans_run_off_the_request_thread(tmp_path):
    svc = _make(tmp_path)
    shutil.copytree(svc.levels / NAME, svc.levels / f"{NAME} [saber-tooth]")
    main = threading.get_ident()
    seen: list[int] = []
    real = background.scan_copy

    def spy(s, folder):
        seen.append(threading.get_ident())
        real(s, folder)

    background.scan_copy = spy
    try:
        svc.refresh_library()
        mid = map_id_for(f"{NAME} [saber-tooth]")
        assert _wait(lambda: svc.store.scan_info(mid) is not None)
    finally:
        background.scan_copy = real
    assert seen and main not in seen


def test_list_query_uses_indexes(tmp_path):
    svc = _make(tmp_path)
    from saber_tooth import store_maps as m

    sql = m._page_sql((0, 0, 0, None, None, (False,) * 4), "title", "ASC")
    plan = " ".join(
        r[3] for r in svc.store._db.execute("EXPLAIN QUERY PLAN " + sql, (40, 0)).fetchall()
    )
    assert "maps_folder" in plan and "proposals_map" in plan
    assert "SCAN f" not in plan and "SCAN p" not in plan
