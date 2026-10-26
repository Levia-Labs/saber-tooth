from pathlib import Path

import pytest

from saber_tooth.store import Store


def _prop(rule: str = "r1") -> dict:
    return {
        "rule": rule,
        "difficulty": "Expert",
        "severity": "warn",
        "summary": "s",
        "ops": [{"op": "remove", "i": 1}],
        "before": {"a": 1},
        "after": {"a": 2},
    }


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "db.sqlite")


def test_upsert_and_list_maps(store: Store) -> None:
    store.upsert_map("m1", "f", "T", "M", "Env", None)
    store.upsert_map("m1", "f2", "T2", "M", "Env", "bad")
    maps = store.list_maps()
    assert len(maps) == 1
    assert maps[0]["folder"] == "f2"
    assert maps[0]["parse_error"] == "bad"


def test_proposal_status_transitions(store: Store) -> None:
    ids = store.add_proposals("m1", [_prop("a"), _prop("b")])
    assert ids == sorted(ids) and len(ids) == 2
    props = store.proposals("m1")
    assert [p["rule"] for p in props] == ["a", "b"]
    assert props[0]["ops"] == [{"op": "remove", "i": 1}]
    assert props[0]["before"] == {"a": 1}
    assert props[0]["after"] == {"a": 2}
    assert props[0]["status"] == "pending"
    assert store.approved("m1") == []
    store.set_status(ids[0], "approved")
    assert [p["id"] for p in store.approved("m1")] == [ids[0]]
    store.set_status(ids[0], "applied")
    assert store.approved("m1") == []
    store.set_status(ids[1], "rejected")
    assert store.proposals("m1")[1]["status"] == "rejected"


def test_set_status_unknown_id_raises(store: Store) -> None:
    with pytest.raises(KeyError):
        store.set_status(999, "approved")


def test_set_status_invalid_status(store: Store) -> None:
    (pid,) = store.add_proposals("m1", [_prop()])
    with pytest.raises(ValueError):
        store.set_status(pid, "bogus")


def test_job_result_round_trips(store: Store) -> None:
    jid = store.create_job("scan")
    assert len(jid) == 32
    assert store.job(jid)["status"] == "queued"
    store.update_job(jid, "done", result={"n": [1, 2], "ok": True})
    job = store.job(jid)
    assert job["status"] == "done"
    assert job["result"] == {"n": [1, 2], "ok": True}
    store.update_job(jid, "failed", error="boom")
    assert store.job(jid)["error"] == "boom"
