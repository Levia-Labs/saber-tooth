# ruff: noqa: F811
import shutil

import pytest

from saber_tooth.fixer import Flip, Move
from saber_tooth.model import Color, Cut, Note
from saber_tooth.service import ApplyConflict, map_id_for
from tests.test_service import NAME, NOTE, _make, _propose, levels, svc  # noqa: F401


def test_refresh_failure_after_commit_keeps_proposals_applied(svc, levels, monkeypatch):
    mid = map_id_for(NAME)
    _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    monkeypatch.setattr(svc, "refresh_library", lambda: (_ for _ in ()).throw(OSError("x")))
    svc.apply(mid)
    assert [p["status"] for p in svc.store.proposals(mid)] == ["applied"]
    with pytest.raises(ApplyConflict):
        svc.apply(mid)
    assert sorted(p.name for p in levels.iterdir() if "saber-tooth" in p.name) == [
        f"{NAME} [saber-tooth]"
    ]


def test_rescan_resets_approved_and_keeps_history(svc):
    mid = map_id_for(NAME)
    approved = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    rejected = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))], status="rejected")
    applied = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))], status="applied")
    svc.scan(mid)
    svc.scan(mid)
    props = svc.store.proposals(mid)
    ids = [p["id"] for p in props]
    assert approved not in ids and rejected in ids and applied in ids
    assert not [p for p in props if p["status"] == "approved"]
    assert len([p for p in props if p["status"] == "pending"]) == len(
        {(p["rule"], p["difficulty"], p["summary"]) for p in props if p["status"] == "pending"}
    )


def test_stale_and_unreadable_maps_raise_clear_errors(svc, levels):
    from saber_tooth.service import MapNotFound, MapUnreadable

    mid = map_id_for(NAME)
    with pytest.raises(MapNotFound):
        svc.scan("deadbeef0000")
    (levels / NAME / "Info.dat").write_text("{", encoding="utf-8")
    svc.refresh_library()
    with pytest.raises(MapUnreadable):
        svc.scan(mid)
    shutil.rmtree(levels / NAME)
    svc.refresh_library()
    assert svc.store.list_maps() == []
    with pytest.raises(MapNotFound):
        svc.apply(mid)


def test_baseline_is_stored_scan_not_current_original(tmp_path):
    svc = _make(tmp_path, env="NiceEnvironment")
    mid = map_id_for(NAME)
    svc.scan(mid)
    info = svc.levels / NAME / "Info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace("NiceEnvironment", "DefaultEnvironment"),
        encoding="utf-8",
    )
    _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    folders = sorted(p.name for p in svc.levels.iterdir())
    with pytest.raises(ApplyConflict, match="default-environment"):
        svc.apply(mid)
    assert sorted(p.name for p in svc.levels.iterdir()) == folders


def test_conflict_failure_job_carries_conflict_ids(tmp_path):
    from saber_tooth.jobs import Jobs

    a = Note(5.0, 0, 0, Color(1), Cut(1))
    b = Note(5.0, 1, 0, Color(0), Cut(1))
    svc = _make(tmp_path, extra=[a, b])
    mid = map_id_for(NAME)
    p1 = _propose(svc, mid, [Move("Hard", a, 2, 2, Cut(1))])
    p2 = _propose(svc, mid, [Move("Hard", b, 2, 2, Cut(1))])
    jobs = Jobs(svc.store)
    jid = jobs.submit("apply", svc.run_apply, mid)
    jobs.future(jid).result(timeout=10)
    job = svc.store.job(jid)
    jobs.shutdown()
    assert job["status"] == "failed" and job["result"] == {"conflict": [p1, p2]}
