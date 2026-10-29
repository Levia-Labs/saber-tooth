"""Scan and Fix work one difficulty and one batch at a time and keep what they finished."""

import time

import pytest

from saber_tooth.fixer import window
from saber_tooth.jobs import JobCancelled
from saber_tooth.service import fixrun, map_id_for
from saber_tooth.service.fixsave import Checkpoint
from tests.test_fix_window import messy
from tests.test_scan_stages import Progress
from tests.test_service import NAME, _make


def _stored(svc, mid) -> int:
    info = svc.store.scan_info(mid)
    return len(info["findings"]) if info else 0


def test_each_batch_is_stored_before_the_next_starts(tmp_path, monkeypatch):
    monkeypatch.setattr(window, "BATCH_NOTES", 20)
    svc = _make(tmp_path, extra=messy(100))
    mid = map_id_for(NAME)
    seen: dict[str, int] = {}

    class Watch(Progress):
        def __call__(self, text):
            super().__call__(text)
            if ": batch " in text:
                seen[text] = _stored(svc, mid)

    out = svc.run_scan(mid, Watch())
    hard = [v for k, v in seen.items() if k.startswith("Hard: batch")]
    assert len(hard) > 3 and hard[0] < hard[-1]  # findings grew while the scan was running
    assert hard == sorted(hard)
    assert {"difficulty": "Hard", "batches": len(hard)} in out["completed"]
    assert _stored(svc, mid) >= hard[-1]


def test_a_cancelled_scan_keeps_the_batches_it_finished(tmp_path, monkeypatch):
    monkeypatch.setattr(window, "BATCH_NOTES", 20)
    svc = _make(tmp_path, extra=messy(100))
    mid = map_id_for(NAME)

    class Stop(Progress):
        def __call__(self, text):
            super().__call__(text)
            if text.startswith("Hard: batch 4"):
                self.stop.set()

    with pytest.raises(JobCancelled):
        svc.run_scan(mid, Stop())
    assert _stored(svc, mid) > 0


def test_scan_of_a_dense_map_stores_early_and_finishes_quickly(tmp_path):
    svc = _make(tmp_path, extra=messy(1500, 3, 0.09))
    mid = map_id_for(NAME)
    first: list[float] = []
    start = time.monotonic()

    class Watch(Progress):
        def __call__(self, text):
            super().__call__(text)
            if text.startswith("Hard: batch 2 of") and not first:
                first.append(time.monotonic() - start)

    out = svc.run_scan(mid, Watch())
    total = time.monotonic() - start
    assert _stored(svc, mid) > 1000 and out["proposals"] > 500
    assert first and first[0] < 30, first  # the first batch is stored within seconds
    assert total < 200, total  # 1500 notes: the whole-map scan needed ~5 minutes


def _stop_at(prefix: str):
    class Stop(Progress):
        def __call__(self, text):
            super().__call__(text)
            if text.startswith(prefix):
                self.stop.set()

    return Stop()


def test_a_cancelled_fix_keeps_its_copy_and_a_retry_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(window, "BATCH_NOTES", 20)
    monkeypatch.setattr(fixrun, "SAVE_BATCHES", 1)
    svc = _make(tmp_path, extra=messy(100))
    mid = map_id_for(NAME)
    with pytest.raises(JobCancelled):
        svc.fix_map(mid, progress=_stop_at("Hard: batch 4"))
    copy = svc.levels / f"{NAME} [saber-tooth]"
    assert copy.is_dir() and Checkpoint(svc.data, mid).path.exists()
    texts = Progress()
    report = svc.fix_map(mid, progress=texts)
    assert report["resumed"] and report["folder"] == copy.name and report["errors"] == 0
    batches = [t for t in texts.texts if t.startswith("Hard: batch ")]
    assert not batches[0].startswith("Hard: batch 1 of")  # earlier batches are not redone
    assert any(c["difficulty"] == "Hard" for c in report["completed"])
    assert not Checkpoint(svc.data, mid).path.exists()
    assert len([p for p in svc.levels.iterdir() if "saber-tooth" in p.name]) == 1


def test_a_failed_fix_names_where_it_stopped_and_keeps_finished_work(tmp_path, monkeypatch):
    monkeypatch.setattr(window, "BATCH_NOTES", 20)
    monkeypatch.setattr(fixrun, "SAVE_BATCHES", 1)
    svc = _make(tmp_path, extra=messy(100))
    real, calls = fixrun.propose_with_reason, []

    def flaky(*args):
        calls.append(1)
        if len(calls) > 25:
            raise RuntimeError("boom")
        return real(*args)

    monkeypatch.setattr(fixrun, "propose_with_reason", flaky)
    with pytest.raises(fixrun.Stopped, match=r"stopped at \w+ batch \d+ of \d+: boom"):
        svc.fix_map(map_id_for(NAME))
    assert (svc.levels / f"{NAME} [saber-tooth]").is_dir()
