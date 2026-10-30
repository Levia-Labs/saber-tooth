"""Worker pool: the concurrency cap, per-map serialisation and resizing, with thread handlers."""

import threading
import time

from saber_tooth.jobs import Jobs
from saber_tooth.store import Store


class Probe:
    """Counts overlapping handler runs, overall and per map."""

    def __init__(self, hold: float = 0.15) -> None:
        self.hold, self.lock = hold, threading.Lock()
        self.now = self.peak = 0
        self.by_map: dict[str | None, int] = {}
        self.map_peak: dict[str | None, int] = {}

    def __call__(self, args, progress):
        key = args.get("map_id")
        with self.lock:
            self.now += 1
            self.peak = max(self.peak, self.now)
            self.by_map[key] = self.by_map.get(key, 0) + 1
            self.map_peak[key] = max(self.map_peak.get(key, 0), self.by_map[key])
        time.sleep(self.hold)
        with self.lock:
            self.now -= 1
            self.by_map[key] -= 1


def pool(tmp_path, limit, kinds=("a",), hold=0.15):
    store = Store(tmp_path / "db.sqlite")
    cap = {"n": limit}
    jobs = Jobs(store, limit=lambda: cap["n"])
    probe = Probe(hold)
    for kind in kinds:
        jobs.register(kind, probe)
    return store, jobs, probe, cap


def test_with_a_cap_of_one_jobs_never_overlap(tmp_path):
    store, jobs, probe, _ = pool(tmp_path, 1)
    ids = [store.create_job("a", None, {}) for _ in range(4)]
    jobs.start()
    assert all(jobs.wait(i, 10)["status"] == "done" for i in ids)
    jobs.shutdown()
    assert probe.peak == 1


def test_with_a_cap_of_two_two_jobs_run_together(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store, limit=lambda: 2)
    both = threading.Barrier(2, timeout=5)  # each waits for the other: only passes in parallel
    jobs.register("a", lambda args, progress: both.wait())
    ids = [store.create_job("a", None, {}) for _ in range(2)]
    jobs.start()
    assert all(jobs.wait(i, 10)["status"] == "done" for i in ids)
    jobs.shutdown()


def test_the_cap_is_never_exceeded(tmp_path):
    store, jobs, probe, _ = pool(tmp_path, 2)
    ids = [store.create_job("a", None, {}) for _ in range(6)]
    jobs.start()
    assert all(jobs.wait(i, 10)["status"] == "done" for i in ids)
    jobs.shutdown()
    assert probe.peak == 2


def test_jobs_on_one_map_are_serialised_while_other_maps_run(tmp_path):
    store, jobs, probe, _ = pool(tmp_path, 4, kinds=("a", "b"))
    same = [store.create_job(kind, "m1", {"map_id": "m1"}) for kind in ("a", "b", "a")]
    other = store.create_job("a", "m2", {"map_id": "m2"})
    jobs.start()
    assert all(jobs.wait(i, 10)["status"] == "done" for i in [*same, other])
    jobs.shutdown()
    assert probe.map_peak["m1"] == 1
    assert probe.peak >= 2  # m2 overlapped one of the m1 jobs


def test_a_blocked_same_map_job_does_not_hold_up_the_queue(tmp_path):
    store, jobs, _, _ = pool(tmp_path, 2, kinds=("a",), hold=0.4)
    first = store.create_job("a", "m1", {"map_id": "m1"})
    second = store.create_job("a", "m1", {"map_id": "m1"})
    third = store.create_job("a", "m2", {"map_id": "m2"})
    jobs.start()
    deadline = time.monotonic() + 5
    while store.job(third)["status"] == "queued" and time.monotonic() < deadline:
        time.sleep(0.01)
    assert store.job(second)["status"] == "queued"  # m1 busy
    assert store.job(third)["status"] in ("running", "done")
    assert all(jobs.wait(i, 10)["status"] == "done" for i in (first, second, third))
    jobs.shutdown()


def test_raising_the_cap_applies_to_jobs_started_afterwards(tmp_path):
    store, jobs, probe, cap = pool(tmp_path, 1, hold=0.3)
    first = [store.create_job("a", None, {}) for _ in range(2)]
    jobs.start()
    for i in first:
        jobs.wait(i, 10)
    assert probe.peak == 1
    cap["n"] = 3
    more = [store.create_job("a", None, {}) for _ in range(3)]
    jobs.poke()
    assert all(jobs.wait(i, 10)["status"] == "done" for i in more)
    jobs.shutdown()
    assert probe.peak == 3


def test_lowering_the_cap_lets_running_jobs_finish(tmp_path):
    store, jobs, probe, cap = pool(tmp_path, 3, hold=0.3)
    ids = [store.create_job("a", None, {}) for _ in range(3)]
    jobs.start()
    while jobs.running_count() < 3:
        time.sleep(0.01)
    cap["n"] = 1
    later = [store.create_job("a", None, {}) for _ in range(2)]
    assert all(jobs.wait(i, 10)["status"] == "done" for i in [*ids, *later])
    jobs.shutdown()
    assert probe.peak == 3 and jobs.running_count() == 0


def test_running_count_tracks_active_jobs(tmp_path):
    store, jobs, _, _ = pool(tmp_path, 2, hold=0.3)
    assert jobs.running_count() == 0
    ids = [store.create_job("a", None, {}) for _ in range(2)]
    jobs.start()
    while jobs.running_count() < 2:
        time.sleep(0.01)
    assert jobs.wait(ids[0], 10)["status"] == "done"
    jobs.shutdown()
    assert jobs.running_count() == 0


def test_a_failing_job_frees_its_slot_and_its_map(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store, limit=lambda: 1)

    def handler(args, progress):
        if args.get("fail"):
            raise RuntimeError("nope")

    jobs.register("a", handler)
    bad = store.create_job("a", "m1", {"fail": True})
    good = store.create_job("a", "m1", {})
    jobs.start()
    assert jobs.wait(bad, 10)["status"] == "failed"
    assert jobs.wait(good, 10)["status"] == "done"
    jobs.shutdown()
