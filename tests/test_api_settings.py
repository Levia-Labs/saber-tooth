"""/api/system, /api/settings and the PlaylistManager routes through the real app."""

import pytest
from fastapi.testclient import TestClient

from saber_tooth import api as api_module
from saber_tooth.api import create_app, settings_api
from tests.test_mods_playlistmanager import FakeMods
from tests.test_service import _make

SNAPSHOT = {
    "cores": 8,
    "memory": {"total": 8 * 2**30, "available": 6 * 2**30, "source": "cgroup"},
    "recommended_max": 4,
    "fix_job_peak_mb": 512,
}


@pytest.fixture
def built(tmp_path, monkeypatch):
    made = []
    real = api_module.Api

    def capture(service):
        made.append(real(service))
        return made[0]

    monkeypatch.setattr(api_module, "Api", capture)
    monkeypatch.setattr(settings_api, "snapshot", lambda: dict(SNAPSHOT))
    app = create_app(_make(tmp_path))
    with TestClient(app, base_url="http://localhost") as client:
        yield client, made[0], tmp_path


def test_system_reports_resources_and_workers(built):
    client, _, _ = built
    got = client.get("/api/system").json()
    assert got["cores"] == 8 and got["recommended_max"] == 4
    assert got["memory"]["source"] == "cgroup"
    assert got["workers"] == {"configured": 1, "running": 0}
    assert got["fix_job_peak_mb"] == 512


def test_settings_default_to_one_worker_and_no_game_folder(built):
    client, _, _ = built
    assert client.get("/api/settings").json() == {
        "max_concurrent_jobs": 1,
        "recommended_max": 4,
        "game_dir": None,
    }


def test_the_cap_can_be_raised_and_the_job_pool_follows(built):
    client, api, _ = built
    got = client.put("/api/settings", json={"max_concurrent_jobs": 3})
    assert got.status_code == 200 and got.json()["max_concurrent_jobs"] == 3
    assert client.get("/api/settings").json()["max_concurrent_jobs"] == 3
    assert api.jobs._limit() == 3
    assert client.get("/api/system").json()["workers"]["configured"] == 3


@pytest.mark.parametrize("value", [0, 5, -1, "2", 1.5, None, True])
def test_a_cap_outside_one_to_the_recommended_maximum_is_refused(built, value):
    client, api, _ = built
    got = client.put("/api/settings", json={"max_concurrent_jobs": value})
    assert got.status_code == 400 and "error" in got.json()
    assert api.jobs._limit() == 1


@pytest.mark.parametrize("body", [[], "x", {"nope": 1}, {}])
def test_unknown_or_empty_settings_bodies_are_refused(built, body):
    client, _, _ = built
    assert client.put("/api/settings", json=body).status_code == 400


def test_post_is_accepted_like_put(built):
    client, _, _ = built
    got = client.post("/api/settings", json={"max_concurrent_jobs": 2})
    assert got.status_code == 200 and got.json()["max_concurrent_jobs"] == 2


def test_a_body_that_is_not_json_is_refused(built):
    client, _, _ = built
    assert client.put("/api/settings", content=b"{").status_code == 400


def test_the_game_folder_is_validated_and_saved(built):
    client, _, tmp_path = built
    assert client.put("/api/settings", json={"game_dir": "relative"}).status_code == 400
    assert client.put("/api/settings", json={"game_dir": str(tmp_path)}).status_code == 400
    game = tmp_path / "game"
    (game / "Beat Saber_Data").mkdir(parents=True)
    got = client.put("/api/settings", json={"game_dir": str(game)})
    assert got.status_code == 200 and got.json()["game_dir"] == str(game.resolve())
    assert client.put("/api/settings", json={"game_dir": ""}).json()["game_dir"] is None


def test_the_mod_status_says_the_game_folder_is_not_mounted(built):
    client, _, _ = built
    got = client.get("/api/mods/playlistmanager").json()
    assert got["game"]["state"] == "not_mounted"
    assert got["mod"]["github"] == "https://github.com/rithik-b/PlaylistManager"
    assert "GAME_DIR_HOST" in got["mount_help"]["env"]


def test_install_needs_an_explicit_confirmation(built):
    client, _, _ = built
    assert client.post("/api/mods/playlistmanager/install", json={}).status_code == 400
    assert client.post("/api/mods/playlistmanager/install").status_code == 400
    refused = client.post("/api/mods/playlistmanager/install", json={"confirm": True})
    assert refused.status_code == 409 and "game folder" in refused.json()["error"]


def test_install_through_the_api_with_a_fake_beatmods(built, monkeypatch):
    client, _, tmp_path = built
    fake = FakeMods()
    monkeypatch.setattr(settings_api, "new_beatmods", lambda: fake)
    game = tmp_path / "Beat Saber"
    (game / "Beat Saber_Data").mkdir(parents=True)
    (game / "BeatSaberVersion.txt").write_text("1.40.8", encoding="utf-8")
    (game / "IPA" / "Data" / "Managed").mkdir(parents=True)
    (game / "IPA" / "Data" / "Managed" / "IPA.Injector.dll").write_bytes(b"ipa")
    assert client.put("/api/settings", json={"game_dir": str(game)}).status_code == 200
    monkeypatch.setattr(settings_api, "game_running", lambda: False)
    import time

    deadline = time.monotonic() + 5
    while client.get("/api/mods/playlistmanager").json()["catalog"]["state"] == "loading":
        assert time.monotonic() < deadline
        time.sleep(0.02)
    assert client.get("/api/mods/playlistmanager").json()["mod"]["can_install"] is True
    got = client.post("/api/mods/playlistmanager/install", json={"confirm": True})
    assert got.status_code == 200
    while client.get("/api/mods/playlistmanager").json()["install"]["state"] == "running":
        assert time.monotonic() < deadline
        time.sleep(0.02)
    assert (game / "Plugins" / "PlaylistManager.dll").read_bytes() == b"pm"


@pytest.mark.parametrize("path", ["/settings", "/vr/settings"])
def test_the_settings_pages_serve_the_app_shell(built, path):
    client, _, _ = built
    got = client.get(path)
    assert got.status_code == 200 and "text/html" in got.headers["content-type"]


def test_a_cross_origin_install_is_refused(built):
    client, _, _ = built
    got = client.post(
        "/api/mods/playlistmanager/install", json={"confirm": True},
        headers={"origin": "https://evil.example"},
    )  # fmt: skip
    assert got.status_code == 403
