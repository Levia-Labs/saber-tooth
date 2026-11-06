from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.api import create_app
from saber_tooth.api.hostpath import host_path
from saber_tooth.service import map_id_for
from tests.crop_helpers import NAME, make_service

seg = st.text(alphabet=st.characters(blacklist_characters="/\\\x00", min_codepoint=33), min_size=1)


@pytest.mark.parametrize(
    ("path", "levels", "host", "want"),
    [
        (
            "/levels/Song",
            "/levels",
            "X:\\Beat Saber\\CustomLevels",
            "X:\\Beat Saber\\CustomLevels\\Song",
        ),
        (
            "/levels/Song",
            "/levels",
            "X:/Beat Saber/CustomLevels/",
            "X:\\Beat Saber\\CustomLevels\\Song",
        ),
        ("/levels/Song", "/levels/", "/srv/maps/maps", "/srv/maps/maps/Song"),
        ("/levels/Song", "/levels", None, "/levels/Song"),
        ("/levels/Song", "/levels", "", "/levels/Song"),
        ("/levels2/Song", "/levels", "/srv/maps", "/levels2/Song"),
        ("/levels", "/levels", "/srv/maps", "/srv/maps"),
    ],
)
def test_host_path_swaps_the_prefix(path, levels, host, want):
    assert host_path(path, levels, host) == want


@given(names=st.lists(seg, min_size=1, max_size=3), tail=seg)
def test_host_path_property(names, tail):
    levels = "/levels"
    inside = "/".join([levels, *names])
    assert host_path(inside, levels, "/h/maps") == "/".join(["/h/maps", *names])
    assert host_path(inside, levels, "X:\\Maps") == "\\".join(["X:\\Maps", *names])
    assert host_path(levels + tail + "/x", levels, "/h") == levels + tail + "/x"


@pytest.fixture
def http(tmp_path, monkeypatch):
    def build(host):
        if host is None:
            monkeypatch.delenv("LEVELS_DIR_HOST", raising=False)
        else:
            monkeypatch.setenv("LEVELS_DIR_HOST", host)
        svc = make_service(tmp_path)
        c = TestClient(create_app(svc), base_url="http://localhost")
        c.svc = svc
        return c

    return build


def test_map_item_folder_path_defaults_to_the_real_path(http):
    c = http(None)
    body = c.get(f"/api/maps/{map_id_for(NAME)}").json()
    assert Path(body["folder_path"]) == c.svc.levels / NAME


def test_map_item_folder_path_uses_levels_dir_host(http):
    c = http("X:\\Beat Saber\\CustomLevels")
    body = c.get(f"/api/maps/{map_id_for(NAME)}").json()
    assert body["folder_path"] == f"X:\\Beat Saber\\CustomLevels\\{NAME}"
