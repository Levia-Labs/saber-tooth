from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.api.jobs_api import list_jobs
from saber_tooth.store import Store
from saber_tooth.store_jobs import FINISHED_CAP, NO_MAP_KEPT

FIN = ("done", "failed", "cancelled")


def _finished(store: Store, map_id: str | None = None) -> list[dict]:
    rows = store._db.execute(
        "SELECT * FROM jobs WHERE status IN ('done','failed','cancelled')"  # noqa: S608
        + (" AND map_id=?" if map_id else " AND map_id IS NULL"),
        (map_id,) if map_id else (),
    ).fetchall()
    return [dict(r) for r in rows]


@settings(max_examples=60, deadline=None)
@given(
    ops=st.lists(
        st.tuples(
            st.sampled_from(["submit", "finish"]),
            st.sampled_from(["a", "b", "c"]),
            st.sampled_from(["fix", "scan"]),
            st.sampled_from(FIN),
        ),
        max_size=40,
    )
)
def test_one_finished_row_per_map_and_active_rows_survive(tmp_path_factory, ops) -> None:
    store = Store(tmp_path_factory.mktemp("db") / "db.sqlite")
    active: set[str] = set()
    for op, map_id, kind, status in ops:
        if op == "submit":
            active.add(store.create_job(kind, map_id))
        else:
            claimed = store.claim_next_job()
            if claimed:
                store.update_job(claimed["id"], status)
                active.discard(claimed["id"])
        for m in ("a", "b", "c"):
            assert len(_finished(store, m)) <= 1
        for job_id in active:
            assert store.job(job_id)["status"] in ("queued", "running")


def test_no_map_jobs_keep_a_few_per_kind(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    for _ in range(NO_MAP_KEPT + 4):
        store.update_job(store.create_job("generate"), "done")
    other = store.create_job("learn")
    store.update_job(other, "done")
    kinds = [r["kind"] for r in _finished(store)]
    assert kinds.count("generate") == NO_MAP_KEPT and kinds.count("learn") == 1


def test_global_cap(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    for i in range(FINISHED_CAP + 5):
        store.update_job(store.create_job("fix", f"m{i}"), "done")
    n = store._db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert n == FINISHED_CAP


def test_startup_prune_clears_seeded_duplicates(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    ids = []
    for i in range(4):
        job_id = store.create_job("fix", "m1")
        store._exec(
            "UPDATE jobs SET status='done', updated_at=? WHERE id=?", (f"2026-01-0{i + 1}", job_id)
        )
        ids.append(job_id)
    other = store.create_job("scan", "m2")
    store._exec("UPDATE jobs SET status='failed' WHERE id=?", (other,))
    queued = store.create_job("fix", "m1")
    assert store.prune_finished_jobs() == 3
    left = {r["id"] for r in store._db.execute("SELECT id FROM jobs").fetchall()}
    assert left == {ids[-1], other, queued}
    assert store.prune_finished_jobs() == 0


def test_list_active_hides_finished_entry(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    store.update_job(store.create_job("fix", "m1"), "done")
    store.update_job(store.create_job("fix", "m2"), "done")
    store.create_job("scan", "m1")
    out = list_jobs(store)
    assert [r["map_id"] for r in out["queued"]] == ["m1"]
    assert [r["map_id"] for r in out["recent"]] == ["m2"]
