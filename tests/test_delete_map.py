import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import MapNotFound, map_id_for
from saber_tooth.service.errors import DeleteRefused
from tests.test_service import NAME, _make

MID = map_id_for(NAME)


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


def test_delete_removes_folder_and_clears_store(svc):
    svc.store.update_job(svc.store.create_job("scan", MID), "done")
    out = svc.delete_map(MID)
    assert out == {"deleted": NAME}
    assert not (svc.levels / NAME).exists()
    assert not (svc.data / "trash").exists()
    assert svc.store.get_map(MID) is None
    assert svc.store.scan_info(MID) is None
    assert svc.store.proposals(MID) == []
    assert svc.store._query("SELECT id FROM jobs WHERE map_id=?", (MID,)) == []


def test_delete_refuses_queued_or_running(svc):
    jid = svc.store.create_job("scan", MID)
    with pytest.raises(DeleteRefused):
        svc.delete_map(MID)
    svc.store.update_job(jid, "running")
    with pytest.raises(DeleteRefused):
        svc.delete_map(MID)
    assert (svc.levels / NAME).exists()


def test_delete_unknown_map(svc):
    with pytest.raises(MapNotFound):
        svc.delete_map("0" * 12)


def test_guard_rejects_outside_levels(svc, tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "keep.txt").write_text("x", encoding="utf-8")
    svc.store.upsert_map(MID, "../elsewhere", "t", "", "", None)
    with pytest.raises(MapNotFound):
        svc.delete_map(MID)
    assert (outside / "keep.txt").exists()


def test_guard_rejects_nested(svc):
    svc.store.upsert_map(MID, f"{NAME}/sub", "t", "", "", None)
    with pytest.raises(MapNotFound):
        svc.delete_map(MID)
    assert (svc.levels / NAME).exists()


def test_symlink_outside_levels_is_refused(svc, tmp_path):
    target = tmp_path / "precious"
    target.mkdir()
    (target / "keep.txt").write_text("x", encoding="utf-8")
    link = svc.levels / "Linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    svc.store.upsert_map(MID, "Linked", "t", "", "", None)
    with pytest.raises(MapNotFound):
        svc.delete_map(MID)
    assert (target / "keep.txt").exists()
    assert link.is_symlink()


@pytest.fixture
def client(svc):
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        yield c


def test_route_deletes(client, svc):
    r = client.delete(f"/api/maps/{MID}")
    assert r.status_code == 200
    assert r.json() == {"deleted": NAME}
    assert client.get(f"/api/maps/{MID}").status_code == 404


def test_route_unknown_is_404(client):
    assert client.delete("/api/maps/" + "0" * 12).status_code == 404
    assert client.delete("/api/maps/nope").status_code == 404


def test_route_busy_is_409(client, svc):
    svc.store.create_job("scan", MID)
    r = client.delete(f"/api/maps/{MID}")
    assert r.status_code == 409
    assert (svc.levels / NAME).exists()


def test_guard_refuses_a_junction(tmp_path, monkeypatch):
    # Windows junctions are directory links that Path.is_symlink() does not report.
    from pathlib import Path

    from saber_tooth.safe_fs import LevelsRoot, WriteRefused

    folder = tmp_path / "Linked"
    folder.mkdir()
    monkeypatch.setattr(Path, "is_junction", lambda self: self == folder)
    with pytest.raises(WriteRefused):
        LevelsRoot(tmp_path).guard(folder)
