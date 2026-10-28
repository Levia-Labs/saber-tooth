import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from tests.crop_helpers import make_service, write_original

TITLES = ["Alpha", "bravo", "Charlie"]


@pytest.fixture
def http(tmp_path):
    svc = make_service(tmp_path)
    for name in TITLES:
        write_original(svc.levels, name)
    svc.refresh_library()
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        c.svc = svc
        yield c


def _listing(http, query=""):
    return http.get(f"/api/maps?limit=100{query}").json()["items"]


def _neighbors(http, folder, query=""):
    return http.get(f"/api/maps/{map_id_for(folder)}/neighbors{query}")


def _ref(item):
    return {"id": item["id"], "title": item["title"], "folder": item["folder"]}


def test_neighbors_follow_the_list_order_with_index_and_total(http):
    items = _listing(http)
    assert len(items) == 4
    body = _neighbors(http, items[1]["folder"]).json()
    assert body == {
        "index": 2,
        "total": 4,
        "prev": _ref(items[0]),
        "next": _ref(items[2]),
    }


def test_the_first_map_wraps_to_the_last_and_the_last_to_the_first(http):
    items = _listing(http)
    first = _neighbors(http, items[0]["folder"]).json()
    last = _neighbors(http, items[-1]["folder"]).json()
    assert first["index"] == 1 and first["prev"] == _ref(items[-1])
    assert last["index"] == 4 and last["next"] == _ref(items[0])


def test_neighbors_honour_sort_order_and_search(http):
    items = _listing(http, "&sort=title&order=desc")
    mid = _neighbors(http, items[1]["folder"], "?sort=title&order=desc").json()
    assert mid["prev"]["id"] == items[0]["id"] and mid["next"]["id"] == items[2]["id"]
    found = _listing(http, "&q=ravo")
    assert len(found) == 1
    only = _neighbors(http, found[0]["folder"], "?q=ravo").json()
    assert only["index"] == 1 and only["total"] == 1
    assert only["prev"] == only["next"] == _ref(found[0])


def test_a_map_outside_the_filtered_list_is_404_with_a_message(http):
    resp = _neighbors(http, "Alpha", "?q=charlie")
    assert resp.status_code == 404 and "not in the filtered list" in resp.json()["error"]


def test_an_unknown_map_and_a_bad_filter(http):
    assert http.get(f"/api/maps/{'0' * 12}/neighbors").status_code == 404
    assert _neighbors(http, "Alpha", "?sort=nope").status_code == 400
