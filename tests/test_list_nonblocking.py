"""The library list stays readable while a fix job runs, and is fast."""

import threading
import time

from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from tests.test_api import MID, _wait
from tests.test_fix_map import CLASH
from tests.test_service import _make


def test_list_not_blocked_by_running_fix_job(tmp_path):
    svc = _make(tmp_path, extra=CLASH)
    started, release = threading.Event(), threading.Event()
    real = svc._reindex

    def slow_refresh():
        started.set()  # the fixed folder is written; the refresh is the slow tail
        release.wait(15)
        return real()

    svc._reindex = slow_refresh
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        jid = http.post(f"/api/maps/{MID}/fix").json()["job"]
        try:
            assert started.wait(10)
            for path in ("/api/maps", "/api/maps/facets"):
                t0 = time.perf_counter()
                resp = http.get(path)
                assert resp.status_code == 200
                assert time.perf_counter() - t0 < 1.0, f"{path} blocked behind the fix job"
        finally:
            release.set()
        assert _wait(http, jid)["status"] == "done"
        assert http.get("/api/maps").status_code == 200
