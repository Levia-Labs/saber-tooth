from pathlib import Path

from saber_tooth.api.jobs_api import core_handlers
from saber_tooth.jobs import Jobs
from saber_tooth.store import Store


def test_a_job_row_without_map_id_in_its_args_uses_the_map_id_column(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store)
    seen: list = []

    class Svc:
        def run_scan(self, map_id, progress=None):
            seen.append(map_id)
            return {"map_id": map_id}

    for kind, handler in core_handlers(Svc()).items():
        jobs.register(kind, handler)
    job_id = store.create_job("scan", "abc123def456")  # no args: was KeyError 'map_id'
    jobs.start()
    row = jobs.wait(job_id)
    jobs.shutdown()
    assert row["status"] == "done" and seen == ["abc123def456"]


def test_args_that_name_a_map_win_over_the_column(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store)
    seen: list = []
    jobs.register("k", lambda args, progress: seen.append(args["map_id"]))
    job_id = store.create_job("k", "col", {"map_id": "arg"})
    jobs.start()
    jobs.wait(job_id)
    jobs.shutdown()
    assert seen == ["arg"]


def test_mapless_scan_rows_keep_only_the_latest_one(tmp_path: Path) -> None:
    """A scan, fix, apply or crop with no map is junk: the list shows one such row, not five."""
    store = Store(tmp_path / "db.sqlite")
    for i in range(3):
        store.update_job(store.create_job("scan", None, {}), "failed", error=f"e{i}")
    for _ in range(3):
        store.update_job(store.create_job("learn", None, {}), "done")
    kinds = [r["kind"] for r in store.job_lists()["recent"]]
    assert kinds.count("scan") == 1 and kinds.count("learn") == 3
