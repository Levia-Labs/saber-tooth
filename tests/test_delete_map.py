import shutil
import time

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


def _client(svc):
    return TestClient(create_app(svc), base_url="http://localhost")


def _fail_refresh(*_a, **_k):
    raise AssertionError("delete must not re-index the whole library")


def test_bulk_delete_route_reports_per_id_without_full_refresh(svc, monkeypatch):
    monkeypatch.setattr(svc, "refresh_library", _fail_refresh)
    out = _client(svc).post("/api/maps/delete", json={"ids": [MID, "0" * 12, MID]})
    assert out.status_code == 200
    body = out.json()
    assert body["deleted"] == 1
    assert [(r["id"], r["status"]) for r in body["results"]] == [
        (MID, "deleted"),
        ("0" * 12, "missing"),
    ]
    assert not (svc.levels / NAME).exists()
    assert svc.store.get_map(MID) is None


def test_bulk_delete_busy_and_validation(svc):
    svc.store.create_job("scan", MID)
    client = _client(svc)
    out = client.post("/api/maps/delete", json={"ids": [MID]}).json()
    assert out["results"][0]["status"] == "busy"
    assert (svc.levels / NAME).exists()
    assert client.post("/api/maps/delete", json={"ids": []}).status_code == 400
    assert client.post("/api/maps/delete", json={"ids": ["../x"]}).status_code == 400
    assert client.post("/api/maps/delete", content=b"nope").status_code == 400
    assert client.post("/api/maps/delete", json={"ids": ["a" * 12] * 501}).status_code == 413


def _grow(svc, n, tag="Filler"):
    for k in range(n):
        shutil.copytree(svc.levels / NAME, svc.levels / f"{tag} {k}")
    svc.refresh_library()


def test_delete_does_not_refresh_and_reindexes_only_the_chain(svc, monkeypatch):
    copy1, copy2 = NAME + " [saber-tooth]", NAME + " [saber-tooth 2]"
    for c in (copy1, copy2):
        shutil.copytree(svc.levels / NAME, svc.levels / c)
    _grow(svc, 5)
    other = map_id_for("Filler 0")
    assert svc.store.get_map(map_id_for(copy1)) is not None
    assert svc.store.get_map(MID)["fixed_copy_id"] == map_id_for(copy1)
    monkeypatch.setattr(svc, "refresh_library", _fail_refresh)
    seen = []
    real = svc._index_folder
    monkeypatch.setattr(svc, "_index_folder", lambda f, p: (seen.append(f.name), real(f, p))[1])
    svc.delete_map(map_id_for(copy1))
    assert sorted(seen) == sorted([NAME, copy2])
    assert svc.store.get_map(map_id_for(copy1)) is None
    assert svc.store.get_map(other) is not None
    ids = [m["id"] for m in svc.store.list_maps()]
    assert map_id_for(copy1) not in ids and MID in ids
    assert svc.store.get_map(MID)["fixed_copy_id"] is None  # pairing with the copy is gone


def test_delete_in_a_200_map_library_is_fast(svc):
    _grow(svc, 199)
    assert len(svc.store.list_maps()) == 200
    start = time.perf_counter()
    svc.delete_map(map_id_for("Filler 7"))
    assert time.perf_counter() - start < 1.0
    start = time.perf_counter()
    out = svc.delete_maps([map_id_for(f"Filler {k}") for k in range(10, 60)])
    assert out["deleted"] == 50
    assert time.perf_counter() - start < 1.0
    assert len(svc.store.list_maps()) == 149
