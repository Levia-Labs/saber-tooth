from pathlib import Path

import pytest

from saber_tooth.api import build_service
from saber_tooth.store import Store
from saber_tooth.store_jobs import INTERRUPTED as MSG


def _set(store: Store, job_id: str, status: str) -> None:
    store._exec("UPDATE jobs SET status=?, updated_at='old' WHERE id=?", (status, job_id))


def test_fail_interrupted_jobs(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    ids = {s: store.create_job("fix", "m1") for s in ("queued", "running", "done", "failed")}
    for s, i in ids.items():
        _set(store, i, s)
    assert store.fail_interrupted_jobs() == 1
    j = store.job(ids["running"])
    assert j["status"] == "failed" and j["error"] == MSG and j["updated_at"] != "old"
    assert store.job(ids["queued"])["status"] == "queued"
    for s in ("done", "failed"):
        assert store.job(ids[s])["updated_at"] == "old"
    assert store.has_active_job("m1")  # the queued row stays
    assert store.fail_interrupted_jobs() == 0


def test_startup_clears_orphaned_jobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LEVELS_DIR", str(tmp_path / "levels"))
    old = Store(tmp_path / "saber-tooth.db")
    old.upsert_map("m1", "f", "T", "M", "Env", None)
    orphan = old.create_job("fix", "m1")
    _set(old, orphan, "running")
    assert old.has_active_job("m1")
    old_status = old.get_map("m1")["status"]
    service = build_service()
    store = service.store
    assert not store.has_active_job("m1")
    assert store.job(orphan)["status"] == "failed"
    assert old_status == "fixing" and store.get_map("m1")["status"] == "incomplete"
    fresh = store.create_job("fix", "m1")
    assert store.job(fresh)["status"] == "queued" and store.has_active_job("m1")
