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


def test_add_proposals_is_atomic(store: Store) -> None:
    with pytest.raises(KeyError):
        store.add_proposals("m1", [_prop(), {"rule": "r"}])
    store.upsert_map("m1", "f", "T", "M", "Env", None)
    assert store.proposals("m1") == []


def _open_prop(rule="r"):
    return {
        "rule": rule,
        "difficulty": "Hard",
        "severity": "warn",
        "summary": "s",
        "ops": [],
        "before": [],
        "after": [],
    }


def test_replace_open_proposals_keeps_history_and_saves_scan(tmp_path):
    from saber_tooth.store import Store

    store = Store(tmp_path / "db.sqlite")
    a, b, c, d = store.add_proposals("m", [_open_prop(), _open_prop(), _open_prop(), _open_prop()])
    store.set_status(b, "approved")
    store.set_status(c, "rejected")
    store.set_status(d, "approved")
    store.mark_applied([d])
    new = store.replace_open_proposals(
        "m", [_open_prop("n")], {"findings": [{"k": 1}], "analysis": "p"}
    )
    statuses = {p["id"]: p["status"] for p in store.proposals("m")}
    assert a not in statuses and b not in statuses
    assert statuses[c] == "rejected" and statuses[d] == "applied" and statuses[new[0]] == "pending"
    assert store.scan_info("m") == {"findings": [{"k": 1}], "analysis": "p"}


def test_proposal_by_id(tmp_path):
    from saber_tooth.store import Store

    store = Store(tmp_path / "db.sqlite")
    p = {"rule": "r", "difficulty": "d", "severity": "warn", "summary": "s"}
    pid = store.add_proposals("m", [{**p, "ops": [], "before": [], "after": []}])[0]
    assert store.proposal(pid)["summary"] == "s" and store.proposal(pid + 1) is None


def test_prune_maps_drops_missing_rows(tmp_path):
    from saber_tooth.store import Store

    store = Store(tmp_path / "db.sqlite")
    store.upsert_map("a", "A", "A", "", "", None)
    store.upsert_map("b", "B", "B", "", "", None)
    store.prune_maps({"a"})
    assert [m["id"] for m in store.list_maps()] == ["a"]


def _library(store: Store) -> None:
    store.upsert_map("a", "fa", "Alpha", "Zed", "Origins", None)
    store.upsert_map("b", "fb", "beta", "Amy", "Nice", None)
    store.upsert_map("c", "fc", "Gamma", "", "", "broken")
    store.upsert_map("d", "fd", "Delta", "Amy", "Nice", None)
    store.upsert_map("e", "fe", "Eps_100%", "Q", "Q", None)
    store.replace_open_proposals(
        "a", [], {"findings": [{"severity": "error"}] * 2 + [{"severity": "warn"}]}
    )
    store.replace_open_proposals("b", [], {"findings": [{"severity": "warn"}]})
    store.replace_open_proposals("d", [], {"findings": []})


def _ids(store: Store, **kw) -> list[str]:
    return [m["id"] for m in store.query_maps(**kw)[0]]


def test_query_maps_status_counts_and_filters(store: Store) -> None:
    _library(store)
    rows, total = store.query_maps(limit=100)
    by_id = {m["id"]: m for m in rows}
    assert total == 5
    assert {k: v["status"] for k, v in by_id.items()} == {
        "a": "error", "b": "warn", "c": "unreadable", "d": "ok", "e": "unscanned",
    }  # fmt: skip
    assert (by_id["a"]["errors"], by_id["a"]["warnings"]) == (2, 1)
    assert by_id["e"]["scanned_at"] is None and by_id["a"]["scanned_at"]
    assert _ids(store, status="warn") == ["b"]
    assert _ids(store, status="ok") == ["d"]


def test_query_maps_sort_order_and_ties(store: Store) -> None:
    _library(store)
    assert _ids(store) == ["a", "b", "d", "e", "c"]  # case-insensitive title
    assert _ids(store, order="desc") == ["c", "e", "d", "b", "a"]
    assert _ids(store, sort="status") == ["c", "a", "b", "e", "d"]
    assert _ids(store, sort="errors", order="desc")[0] == "a"
    assert _ids(store, sort="mapper")[:1] == ["c"]  # empty mapper first
    assert _ids(store, sort="environment")[-1] == "e"
    assert _ids(store, sort="scanned_at")[-2:] == ["e", "c"]
    # ties break by title then id, so pages never overlap
    pages = [_ids(store, sort="mapper", offset=o, limit=2) for o in (0, 2, 4)]
    assert sorted(i for p in pages for i in p) == ["a", "b", "c", "d", "e"]


def test_query_maps_search_is_literal_and_case_insensitive(store: Store) -> None:
    _library(store)
    assert _ids(store, q="AMY") == ["b", "d"]
    assert _ids(store, q="fc") == ["c"]
    assert _ids(store, q="100%") == ["e"]
    assert _ids(store, q="%") == ["e"]
    assert _ids(store, q="'; DROP TABLE maps;--") == []
    assert len(store.list_maps()) == 5
    assert store.query_maps(q="amy", limit=1) == ([store.get_map("b")], 2)


def test_query_maps_rejects_unlisted_keys(store: Store) -> None:
    for bad in ({"sort": "id; DROP TABLE maps"}, {"order": "sideways"}, {"status": "x"}):
        with pytest.raises(ValueError):
            store.query_maps(**bad)
    assert store.get_map("nope") is None
