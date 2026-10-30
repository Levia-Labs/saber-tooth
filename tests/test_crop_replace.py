# ruff: noqa: F811
import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.audio import AudioError
from saber_tooth.crop.replace import replace_folder
from saber_tooth.mapio import load_map
from saber_tooth.safe_fs import WriteRefused
from saber_tooth.service import map_id_for
from tests.crop_helpers import NAME, cuts, make_service, write_original  # noqa: F401
from tests.test_api import _wait
from tests.test_mcp import rpc
from tests.test_service import _hashes

MID = map_id_for(NAME)
BODY = {"start_beat": 0.0, "end_beat": 128.0, "replace": True}


@pytest.fixture
def http(tmp_path):
    svc = make_service(tmp_path)
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        c.svc = svc
        yield c


def _leftovers(levels):
    return sorted(p.name for p in levels.iterdir() if p.name.startswith("."))


def test_replace_writes_the_cropped_content_under_the_original_name_and_id(http, cuts):
    levels = http.svc.levels
    before = _hashes(levels / NAME)
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=BODY).json()["job"])
    assert job["status"] == "done", job
    assert job["result"]["replaced"] is True
    assert job["result"]["folder"] == NAME and job["result"]["cropped_id"] == MID
    assert sorted(p.name for p in levels.iterdir()) == [NAME]
    assert _hashes(levels / NAME) != before
    assert (levels / NAME / "song.ogg").read_bytes() == b"cut"
    assert load_map(levels / NAME).difficulties
    assert http.get(f"/api/maps/{MID}").json()["folder"] == NAME


def test_replace_resets_the_store_rows_but_keeps_the_running_job(http, cuts):
    store = http.svc.store
    http.svc.scan(MID)
    store.update_job(store.create_job("scan", MID), "done")
    assert store.scan_info(MID) is not None
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=BODY).json()["job"])
    assert job["status"] == "done"
    assert store.scan_info(MID)["analysis"] is None and store.proposals(MID) == []  # fresh scan
    rows = store._query("SELECT id, kind FROM jobs WHERE map_id=?", (MID,))
    assert [(r["id"], r["kind"]) for r in rows] == [(job["id"], "crop")]
    assert http.get(f"/api/maps/{MID}").json()["status"] in {"ok", "warn", "error"}


def test_replace_failing_before_the_swap_leaves_the_original(http, cuts, monkeypatch):
    def boom(*args):
        raise AudioError("ffmpeg failed")

    monkeypatch.setattr("saber_tooth.crop.write.cut_egg", boom)
    before = _hashes(http.svc.levels / NAME)
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=BODY).json()["job"])
    assert job["status"] == "failed"
    assert _hashes(http.svc.levels / NAME) == before
    assert _leftovers(http.svc.levels) == []


def test_replace_failing_the_read_back_leaves_the_original(http, cuts, monkeypatch):
    def boom(folder):
        raise OSError("unreadable")

    monkeypatch.setattr("saber_tooth.service.crop.load_map", boom)
    before = _hashes(http.svc.levels / NAME)
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=BODY).json()["job"])
    assert job["status"] == "failed"
    assert _hashes(http.svc.levels / NAME) == before
    assert _leftovers(http.svc.levels) == []


def test_replace_failing_during_the_swap_rolls_back(http, cuts, monkeypatch):
    real = type(http.svc.levels).rename

    def flaky(self, target):
        if self.name == f".{NAME} [1 min].partial":
            raise OSError("swap failed")
        return real(self, target)

    monkeypatch.setattr(type(http.svc.levels), "rename", flaky)
    before = _hashes(http.svc.levels / NAME)
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=BODY).json()["job"])
    assert job["status"] == "failed"
    assert _hashes(http.svc.levels / NAME) == before
    assert _leftovers(http.svc.levels) == []


def test_replace_busy_map_is_409(http, cuts):
    http.svc.store.create_job("scan", MID)
    resp = http.post(f"/api/maps/{MID}/crop", json=BODY)
    assert resp.status_code == 409


def test_replace_validates_the_window_like_a_normal_crop(http, cuts):
    body = {"start_beat": 5, "end_beat": 6.8, "replace": True}
    resp = http.post(f"/api/maps/{MID}/crop", json=body)
    assert resp.status_code == 422 and "at least 1 second" in resp.json()["error"]


def test_replace_must_be_a_boolean(http, cuts):
    resp = http.post(f"/api/maps/{MID}/crop", json={**BODY, "replace": "yes"})
    assert resp.status_code == 422 and "replace" in resp.json()["error"]


def _link(tmp_path, target, link):
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks need privileges here")


def test_a_symlinked_folder_is_refused(tmp_path):
    levels = tmp_path / "levels"
    levels.mkdir()
    real = tmp_path / "elsewhere"
    real.mkdir()
    (real / "Info.dat").write_text("{}", encoding="utf-8")
    _link(tmp_path, real, levels / "Linked")
    partial = levels / ".new.partial"
    partial.mkdir()
    with pytest.raises(WriteRefused):
        replace_folder(levels, levels / "Linked", partial)
    assert (real / "Info.dat").exists() and not partial.exists()


def test_a_folder_outside_the_levels_root_is_refused(tmp_path):
    levels = tmp_path / "levels"
    levels.mkdir()
    outside = write_original(tmp_path, "Outside")
    partial = levels / ".new.partial"
    partial.mkdir()
    with pytest.raises(WriteRefused):
        replace_folder(levels, outside, partial)
    assert outside.is_dir()


def test_mcp_crop_map_has_no_replace_option(http):
    tools = rpc(http, "tools/list").json()["result"]["tools"]
    crop = next(t for t in tools if t["name"] == "crop_map")
    assert "replace" not in crop["inputSchema"]["properties"]
