"""Health endpoint and background library warm-up."""

import time

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from tests.test_service import _make


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


def test_health_is_cheap(svc, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("health touched the library")

    monkeypatch.setattr(svc, "refresh_if_changed", boom)
    monkeypatch.setattr(svc, "refresh_library", boom)
    with TestClient(create_app(svc), base_url="http://127.0.0.1:8100") as c:
        res = c.get("/api/health")
    assert res.status_code == 200 and res.json() == {"status": "ok"}


def test_warm_indexes_in_background(svc):
    with TestClient(create_app(svc, warm=True), base_url="http://localhost") as c:
        for _ in range(100):
            if c.get("/api/maps/facets").json()["total"]:
                break
            time.sleep(0.05)
        assert c.get("/api/maps/facets").json()["total"] >= 1
