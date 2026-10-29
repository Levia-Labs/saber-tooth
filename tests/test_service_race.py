# ruff: noqa: F811
import threading

import pytest

from saber_tooth.analyser_client import AnalyserError
from saber_tooth.fixer import Flip, Move
from saber_tooth.model import Color, Cut, Note
from saber_tooth.service import ApplyConflict, map_id_for
from saber_tooth.service import core as core_module
from saber_tooth.store import ProposalApplied
from tests.test_service import NAME, NOTE, _hashes, _make, _propose, levels, svc  # noqa: F401


class SlowAnalyser:
    """analyse_file blocks until released, then reports a failure (no analysis)."""

    uploads = None

    def __init__(self) -> None:
        self.started, self.release = threading.Event(), threading.Event()

    def analyse_file(self, path, name, cancel=None):
        self.started.set()
        self.release.wait(10)
        raise AnalyserError("stop")


def test_slow_analyser_does_not_block_library_refresh(svc):
    slow, mid = SlowAnalyser(), map_id_for(NAME)
    svc.client = slow
    worker = threading.Thread(target=svc.scan, args=(mid,))
    worker.start()
    try:
        assert slow.started.wait(5)
        (svc.levels / "Other").mkdir()  # the listing changed, so refresh needs the lock
        done = threading.Event()
        threading.Thread(target=lambda: (svc.refresh_if_changed(), done.set())).start()
        assert done.wait(5), "refresh blocked behind the analyser call"
    finally:
        slow.release.set()
        worker.join(10)
    assert not worker.is_alive()


@pytest.mark.parametrize("exc", [OSError("gone"), KeyError("meta")])
def test_analyser_side_failures_degrade_to_no_analysis(svc, exc):
    class Broken:
        uploads = None

        def analyse_file(self, path, name, cancel=None):
            raise exc

    svc.client = Broken()
    assert svc.run_scan(map_id_for(NAME))["analysis"] is False


def test_rejected_during_apply_is_skipped_not_applied(tmp_path, monkeypatch):
    extra = Note(5.0, 2, 0, Color(0), Cut(1))
    svc, mid = _make(tmp_path, extra=[extra]), map_id_for(NAME)
    keep = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    dropped = _propose(svc, mid, [Flip("Hard", extra, Cut(0))])
    real, calls = svc._apply_fixes, []

    def racing(map_id, approved, unchanged, progress=None):
        if not calls:
            svc.store.set_status(dropped, "rejected")  # the reviewer rejects mid-apply
        calls.append([p["id"] for p in approved])
        return real(map_id, approved, unchanged)

    monkeypatch.setattr(svc, "_apply_fixes", racing)
    svc.apply(mid)
    assert calls == [[keep, dropped], [keep]]
    status = {p["id"]: p["status"] for p in svc.store.proposals(mid)}
    assert status == {keep: "applied", dropped: "rejected"}


def test_mark_applied_skips_proposals_no_longer_approved(svc):
    mid = map_id_for(NAME)
    a = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    b = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))], status="rejected")
    svc.store.mark_applied([a, b])
    assert {p["id"]: p["status"] for p in svc.store.proposals(mid)} == {a: "applied", b: "rejected"}


def test_approved_proposals_that_together_create_a_finding_abort_apply(tmp_path):
    red, blue = Note(5.0, 1, 0, Color(0), Cut(1)), Note(5.0, 2, 0, Color(1), Cut(1))
    svc = _make(tmp_path, extra=[red, blue])
    mid = map_id_for(NAME)
    p1 = _propose(svc, mid, [Move("Hard", red, 3, 1, Cut(1))])
    p2 = _propose(svc, mid, [Move("Hard", blue, 0, 1, Cut(1))])
    folders, hashes = sorted(p.name for p in svc.levels.iterdir()), _hashes(svc.levels / NAME)
    with pytest.raises(ApplyConflict, match="crossover") as err:
        svc.apply(mid)
    assert sorted(err.value.ids) == [p1, p2]
    assert sorted(p.name for p in svc.levels.iterdir()) == folders
    assert _hashes(svc.levels / NAME) == hashes
    assert {p["status"] for p in svc.store.proposals(mid)} == {"approved"}


def test_reject_after_final_check_is_refused_not_written_and_rejected(tmp_path, monkeypatch):
    svc, mid = _make(tmp_path), map_id_for(NAME)
    pid = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    real, seen = core_module.write_fixed, []

    def racing(*args, **kwargs):
        with pytest.raises(ProposalApplied):  # the reviewer rejects between check and write
            svc.store.set_status(pid, "rejected")
        seen.append(svc.store.proposal(pid)["status"])
        return real(*args, **kwargs)

    monkeypatch.setattr(core_module, "write_fixed", racing)
    svc.apply(mid)
    assert seen == ["applying"]
    assert svc.store.proposal(pid)["status"] == "applied"


def test_failed_write_releases_the_claim(tmp_path, monkeypatch):
    svc, mid = _make(tmp_path), map_id_for(NAME)
    pid = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(core_module, "write_fixed", boom)
    with pytest.raises(OSError):
        svc.apply(mid)
    assert svc.store.proposal(pid)["status"] == "approved"
