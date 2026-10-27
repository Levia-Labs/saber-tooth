# ruff: noqa: F811
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.beatsaver.params import parse_search
from tests.test_api import _wait, svc  # noqa: F401
from tests.test_api_beatsaver import bs, make_app, upstream  # noqa: F401
from tests.test_mcp import call, rpc


def test_config_and_export(svc, upstream, tmp_path):
    with TestClient(make_app(svc, upstream), base_url="http://localhost") as off:
        assert off.get("/api/beatsaver/config").json() == {"playlists_enabled": False}
        body = {"title": "Mix", "ids": ["3a1f4"]}
        assert off.post("/api/beatsaver/playlist-export", json=body).status_code == 404
    out = tmp_path / "Playlists"
    out.mkdir()
    with TestClient(make_app(svc, upstream, out), base_url="http://localhost") as on:
        assert on.get("/api/beatsaver/config").json() == {"playlists_enabled": True}
        resp = on.post("/api/beatsaver/playlist-export", json={"title": "Mix", "ids": ["3a1f4"]})
        path = Path(resp.json()["path"])
        assert path.parent == out and path.name == "Mix.bplist"
        assert json.loads(path.read_text(encoding="utf-8"))["songs"][0]["key"] == "3a1f4"
        again = on.post("/api/beatsaver/playlist-export", json={"title": "Mix", "ids": ["3a1f4"]})
        assert Path(again.json()["path"]).name == "Mix (2).bplist"
        for bad in ({"title": "", "ids": ["3a1f4"]}, {"title": "x", "ids": []}, {"ids": ["a"]}):
            assert on.post("/api/beatsaver/playlist-export", json=bad).status_code == 400


def test_presets_seeded_once_add_delete(svc, upstream):
    with TestClient(make_app(svc, upstream), base_url="http://localhost") as c:
        presets = c.get("/api/beatsaver/presets").json()
        assert [p["name"] for p in presets] == ["Gentle full-spread hits"] and presets[0]["seeded"]
        f = presets[0]["filters"]
        assert f["diffs"] == "Easy,Normal,Hard" and f["min_rating"] == "0.95"
        assert f["nps_min"] == "1" and f["nps_max"] == "2" and f["order"] == "Rating"
        assert "drum-and-bass" in f["tags"].split(",") and f["diffs_mode"] == "all"
        parse_search(f)  # the seeded filters are valid search parameters
        made = c.post("/api/beatsaver/presets", json={"name": "Mine", "filters": {"q": "x"}})
        assert made.status_code == 200 and made.json()["filters"] == {"q": "x"}
        assert made.json()["seeded"] is False
        dup = c.post("/api/beatsaver/presets", json={"name": "Mine", "filters": {}})
        assert dup.status_code == 409
        pid = made.json()["id"]
        assert c.delete(f"/api/beatsaver/presets/{pid}").status_code == 200
        assert c.delete(f"/api/beatsaver/presets/{pid}").status_code == 404
        assert c.delete("/api/beatsaver/presets/abc").status_code == 404
        seeded = presets[0]["id"]
        assert c.delete(f"/api/beatsaver/presets/{seeded}").status_code == 200
    with TestClient(make_app(svc, upstream), base_url="http://localhost") as again:
        assert again.get("/api/beatsaver/presets").json() == []  # not seeded a second time


@pytest.mark.parametrize(
    "body",
    [
        {"name": "", "filters": {}},
        {"name": "x" * 81, "filters": {}},
        {"name": "x", "filters": {"evil": "1"}},
        {"name": "x", "filters": {"min_rating": "7"}},
        {"name": "x", "filters": {"q": 5}},
        {"name": "x", "filters": []},
        {"name": 5, "filters": {}},
        {"filters": {}},
        [],
    ],
)
def test_preset_validation(bs, body):
    assert bs.post("/api/beatsaver/presets", json=body).status_code == 400


def test_bs_routes_do_not_fall_through_to_spa(bs):
    resp = bs.get("/api/beatsaver/nothing")
    assert resp.status_code == 404 and "error" in resp.json()


def test_mcp_tools(bs, upstream):
    init = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t"}}
    rpc(bs, "initialize", init)
    tools = {t["name"]: t for t in rpc(bs, "tools/list", ident=2).json()["result"]["tools"]}
    assert {"beatsaver_search", "beatsaver_download"} <= set(tools)
    assert tools["beatsaver_search"]["annotations"]["readOnlyHint"] is True
    assert tools["beatsaver_download"]["annotations"]["readOnlyHint"] is False
    found = call(bs, "beatsaver_search", diffs="Easy,Normal,Hard")["structuredContent"]
    assert [i["id"] for i in found["items"]] == ["3a1f4"]
    job = call(bs, "beatsaver_download", ids=["3a1f4"])["structuredContent"]["job"]
    assert _wait(bs, job)["result"]["results"][0]["status"] == "installed"
    bad = call(bs, "beatsaver_search", min_rating=5)
    assert bad["isError"] is True


@given(
    st.dictionaries(
        st.sampled_from(
            [
                "q",
                "tags",
                "min_rating",
                "nps_min",
                "nps_max",
                "nps_scope",
                "diffs",
                "diffs_mode",
                "ranked",
                "order",
                "ascending",
                "from",
                "to",
                "bpm_min",
                "bpm_max",
                "duration_min",
                "duration_max",
                "cursor",
                "limit",
            ]
        ),
        st.text(max_size=50),
        max_size=8,
    )
)
def test_parse_search_never_fails_unexpectedly(params):
    try:
        sp = parse_search(params)
    except ValueError:
        return
    assert 1 <= sp.limit <= 100
    for v in (sp.local.nps_min, sp.local.nps_max):
        assert v is None or 0 <= v <= 30
    assert sp.local.min_rating is None or 0 <= sp.local.min_rating <= 1
    assert all("," not in t and "|" not in t for t in sp.server.tags)
