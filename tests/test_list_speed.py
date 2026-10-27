"""Listing the library stays fast: media checks are cached per folder."""

import shutil
import time

from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from tests.test_service import NAME, _make


def test_list_of_150_maps_is_fast(tmp_path):
    svc = _make(tmp_path)
    for i in range(149):
        shutil.copytree(svc.levels / NAME, svc.levels / f"Song {i}")
    svc.refresh_if_changed()
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        http.get("/api/maps?limit=100")
        t0 = time.perf_counter()
        resp = http.get("/api/maps?limit=100")
        elapsed = time.perf_counter() - t0
    assert resp.status_code == 200 and resp.json()["total"] == 150
    assert elapsed < 1.0, f"list took {elapsed:.2f}s"


def test_media_cache_follows_folder_changes(tmp_path):
    svc = _make(tmp_path)
    with TestClient(create_app(svc), base_url="http://localhost") as http:
        before = http.get("/api/maps").json()["items"][0]
        assert before["audio_url"] or before["cover_url"], "fixture has no media to track"
        for f in (svc.levels / NAME).iterdir():
            if f.suffix.lower() in (".ogg", ".egg", ".jpg", ".png", ".jpeg"):
                f.unlink()
        after = http.get("/api/maps").json()["items"][0]
    assert after["audio_url"] is None and after["cover_url"] is None
