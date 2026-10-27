"""Cache headers for the built frontend: hashed assets are immutable, the shell is revalidated."""

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from tests.test_service import NAME, _make

IMMUTABLE = "public, max-age=31536000, immutable"


@pytest.fixture
def client(tmp_path):
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (web / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    (web / "assets" / "index-abc123.js").write_text("export {};", encoding="utf-8")
    (tmp_path / "svc").mkdir()
    service = _make(tmp_path / "svc")
    with TestClient(create_app(service, web=web), base_url="http://localhost") as c:
        yield c


def test_hashed_assets_are_immutable(client):
    resp = client.get("/assets/index-abc123.js")
    assert resp.status_code == 200 and resp.headers["cache-control"] == IMMUTABLE


def test_index_is_revalidated_at_root_and_on_spa_routes(client):
    for path in ("/", "/index.html", "/new", f"/maps/{map_id_for(NAME)}"):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert resp.headers["cache-control"] == "no-cache", path


def test_other_static_files_are_revalidated(client):
    assert client.get("/favicon.svg").headers["cache-control"] == "no-cache"


def test_missing_asset_is_404_without_immutable_header(client):
    resp = client.get("/assets/missing.js")
    assert resp.status_code == 404 and "immutable" not in resp.headers.get("cache-control", "")
