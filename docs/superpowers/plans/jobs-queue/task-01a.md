### Task 1: Durable job rows in the store

**Files:**

- Create: `src/saber_tooth/store_jobs.py`
- Modify: `src/saber_tooth/store.py` (schema at lines 20-22, `_INDEXES` line 31, `_MIGRATIONS` lines 33-42, class line 53, job methods lines 253-281)
- Modify: `src/saber_tooth/store_claims.py` (remove `INTERRUPTED` and `fail_interrupted_jobs`, lines 10-27)
- Modify: `src/saber_tooth/README.md` (add the `store_jobs.py` row)
- Test: `tests/test_store_jobs.py` (new), `tests/test_store_interrupted.py` (update)

**Interfaces:**

- Produces (all on `Store`):
  - `create_job(kind: str, map_id: str | None = None, args: dict | None = None, dedupe: bool = False) -> str`
  - `update_job(id: str, status: str, error: str | None = None, result: Any = None) -> None` (unchanged)
  - `job(id: str) -> dict` (unchanged shape plus the new columns; `args_json` removed, `args` dict added)
  - `claim_next_job() -> dict | None` (row as returned by `job`, status already `running`, plus the raw `args_json` string)
  - `set_job_progress(id: str, text: str) -> None`
  - `cancel_job(id: str) -> str` returns `"cancelled"` or the job's current status; raises `KeyError` for an unknown id
  - `job_lists(now: datetime | None = None) -> dict[str, list[dict]]` keys `running`, `queued`, `recent`; rows carry the job columns minus `result_json`/`args_json`, plus `args` (dict), `map_title` (str | None), `map_exists` (bool)
  - `queue_position(id: str) -> int | None`
  - `fail_interrupted_jobs() -> int` now fails only `running` rows
  - module constants `INTERRUPTED`, `RECENT_HOURS = 24`, `RECENT_LIMIT = 50`

- [ ] **Step 1: Write the failing tests**

`tests/test_store_jobs.py`:

```python
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from saber_tooth.store import Store
from saber_tooth.store_jobs import INTERRUPTED, RECENT_LIMIT


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "db.sqlite")


def test_old_database_gains_the_new_columns(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE jobs(id TEXT PRIMARY KEY, kind TEXT, status TEXT, error TEXT,"
        " result_json TEXT, created_at TEXT, updated_at TEXT)"
    )
    db.commit()
    db.close()
    s = Store(path)
    job_id = s.create_job("fix", "m1", {"map_id": "m1"})
    row = s.job(job_id)
    assert row["args"] == {"map_id": "m1"}
    assert row["started_at"] is None and row["progress"] is None and row["progress_at"] is None


def test_claim_takes_oldest_first_and_marks_running(store: Store) -> None:
    a = store.create_job("scan", "m1", {"map_id": "m1"})
    b = store.create_job("scan", "m2", {"map_id": "m2"})
    first = store.claim_next_job()
    assert first is not None and first["id"] == a and first["status"] == "running"
    assert first["started_at"] is not None and first["args"] == {"map_id": "m1"}
    second = store.claim_next_job()
    assert second is not None and second["id"] == b
    assert store.claim_next_job() is None


def test_two_threads_never_claim_the_same_row(store: Store) -> None:
    ids = {store.create_job("scan", f"m{i}", {}) for i in range(40)}
    claimed: list[str] = []
    lock = threading.Lock()

    def drain() -> None:
        while (row := store.claim_next_job()) is not None:
            with lock:
                claimed.append(row["id"])

    threads = [threading.Thread(target=drain) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(claimed) == sorted(ids)


def test_dedupe_returns_the_active_job_of_the_same_kind(store: Store) -> None:
    a = store.create_job("fix", "m1", {"map_id": "m1"}, dedupe=True)
    assert store.create_job("fix", "m1", {"map_id": "m1"}, dedupe=True) == a
    assert store.create_job("scan", "m1", {"map_id": "m1"}, dedupe=True) != a
    assert store.create_job("fix", "m2", {"map_id": "m2"}, dedupe=True) != a
    store.claim_next_job()  # a is running now; still deduped
    assert store.create_job("fix", "m1", {"map_id": "m1"}, dedupe=True) == a
    store.update_job(a, "done")
    assert store.create_job("fix", "m1", {"map_id": "m1"}, dedupe=True) != a


def test_cancel_only_queued(store: Store) -> None:
    a = store.create_job("scan", "m1", {})
    b = store.create_job("scan", "m2", {})
    store.claim_next_job()  # a running
    assert store.cancel_job(a) == "running"
    assert store.cancel_job(b) == "cancelled"
    assert store.job(b)["status"] == "cancelled"
    assert store.claim_next_job() is None  # b is never claimed
    store.update_job(a, "done")
    assert store.cancel_job(a) == "done"
    with pytest.raises(KeyError):
        store.cancel_job("0" * 32)


def test_cancel_and_claim_race_has_one_winner(store: Store) -> None:
    for _ in range(30):
        job_id = store.create_job("scan", None, {})
        out: dict[str, object] = {}
        t1 = threading.Thread(target=lambda: out.update(claim=store.claim_next_job()))
        t2 = threading.Thread(target=lambda: out.update(cancel=store.cancel_job(job_id)))
        for t in (t1, t2):
            t.start()
        for t in (t1, t2):
            t.join()
        claimed = out["claim"] is not None
        assert claimed != (out["cancel"] == "cancelled")
        assert store.job(job_id)["status"] == ("running" if claimed else "cancelled")
        if claimed:
            store.update_job(job_id, "done")


def test_progress_is_written(store: Store) -> None:
    a = store.create_job("fix", "m1", {})
    store.claim_next_job()
    store.set_job_progress(a, "round 2 of 6")
    row = store.job(a)
    assert row["progress"] == "round 2 of 6" and row["progress_at"] is not None


def test_lists_positions_titles_and_recent_limits(store: Store) -> None:
    store.upsert_map("m1", "Folder One", "Song One", "Mapper", "Default")
    run = store.create_job("fix", "m1", {"map_id": "m1"})
    q1 = store.create_job("scan", "gone", {"map_id": "gone"})
    q2 = store.create_job("generate", None, {"url": "https://youtu.be/x"})
    store.claim_next_job()
    lists = store.job_lists()
    assert [j["id"] for j in lists["running"]] == [run]
    assert [j["id"] for j in lists["queued"]] == [q1, q2]
    assert lists["running"][0]["map_title"] == "Song One" and lists["running"][0]["map_exists"]
    assert lists["queued"][0]["map_title"] is None and not lists["queued"][0]["map_exists"]
    assert lists["queued"][1]["args"] == {"url": "https://youtu.be/x"}
    assert "result_json" not in lists["running"][0] and "args_json" not in lists["running"][0]
    assert store.queue_position(q1) == 1 and store.queue_position(q2) == 2
    assert store.queue_position(run) is None


def test_recent_keeps_24_hours_and_at_most_50(store: Store) -> None:
    for _ in range(RECENT_LIMIT + 5):
        store.update_job(store.create_job("scan", None, {}), "done")
    last = store.create_job("scan", None, {})
    store.update_job(last, "failed", error="x")
    later = datetime.now(UTC) + timedelta(hours=25)
    assert store.job_lists(now=later)["recent"] == []
    recent = store.job_lists()["recent"]
    assert len(recent) == RECENT_LIMIT and recent[0]["id"] == last  # newest first


def test_restart_fails_running_and_keeps_queued(store: Store) -> None:
    a = store.create_job("scan", None, {})
    b = store.create_job("scan", None, {})
    store.claim_next_job()
    assert store.fail_interrupted_jobs() == 1
    assert store.job(a)["status"] == "failed" and store.job(a)["error"] == INTERRUPTED
    assert store.job(b)["status"] == "queued"
```

Note for the implementer: check `upsert_map`'s real signature in `store.py:80` and pass the title in the right position; the assertions need `title == "Song One"`.

In `tests/test_store_interrupted.py`, change every assertion that a `queued` row becomes `failed` after `fail_interrupted_jobs` so it now asserts the row stays `queued`; rows that were `running` still fail with `INTERRUPTED`. Import `INTERRUPTED` from `saber_tooth.store_jobs`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `task st:test -- tests/test_store_jobs.py tests/test_store_interrupted.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'saber_tooth.store_jobs'`.

Continued in [task-01b.md](task-01b.md).
