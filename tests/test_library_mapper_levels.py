# ruff: noqa: F811
import sqlite3

import pytest
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.api.library import MAPPER_SEP, parse_query
from saber_tooth.store import Store
from saber_tooth.store_maps import LEVEL_NAMES, level_mask
from tests.test_api import client, svc  # noqa: F401

E, N, H, X, P = (1 << i for i in range(5))


def _store(tmp_path) -> Store:
    store = Store(tmp_path / "db.sqlite")
    store.upsert_map("a", "a", "A", "Zed", "E1", None, None, None, E | N)
    store.upsert_map("b", "b", "B", "Yan, Jr", "E1", None, None, None, X | P)
    store.upsert_map("c", "c", "C", "Zed", "E2", None, None, None, P)
    store.upsert_map("d", "d", "D", "", "E2", None, None, None, None)
    store.upsert_map("e", "e", "E", "Yan", "E2", None, None, None, H)
    return store


def _ids(store, **kw) -> str:
    return "".join(r["id"] for r in store.query_maps(**kw)[0])


def test_mapper_filter_is_exact_and_repeatable(tmp_path):
    s = _store(tmp_path)
    assert _ids(s, mapper=("Zed",)) == "ac"
    assert _ids(s, mapper=("Yan, Jr", "Yan")) == "be"
    assert _ids(s, mapper=("zed",)) == "" and _ids(s, mapper=("Ze",)) == ""
    assert _ids(s, mapper=("Zed",), env=("E2",)) == "c"


def test_level_filter_any_and_all(tmp_path):
    s = _store(tmp_path)
    assert _ids(s, level=("Easy", "Hard")) == "ae"
    assert _ids(s, level=("Expert", "ExpertPlus"), level_mode="any") == "bc"
    assert _ids(s, level=("Expert", "ExpertPlus"), level_mode="all") == "b"
    assert _ids(s, level=("Easy",), mapper=("Zed",), q="a", q_fields="title") == "a"


def test_q_fields_title_and_mapper_are_separate(tmp_path):
    s = _store(tmp_path)
    assert _ids(s, q="yan", q_fields="title") == ""
    assert _ids(s, q="yan", q_fields="mapper") == "be"
    assert _ids(s, q="b", q_fields="title") == "b"


def test_sort_levels_highest_then_count_nulls_last(tmp_path):
    s = _store(tmp_path)
    assert _ids(s, sort="levels", order="asc") == "aecbd"
    assert _ids(s, sort="levels", order="desc") == "bcead"


def test_sort_mapper(tmp_path):
    assert _ids(_store(tmp_path), sort="mapper") == "debac"


def test_invalid_filters_rejected(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ValueError):
        s.query_maps(level=("Nope",))
    with pytest.raises(ValueError):
        s.query_maps(level_mode="some")
    with pytest.raises(ValueError):
        s.query_maps(mapper=tuple(str(i) for i in range(51)))


def test_facets_mappers_and_levels(tmp_path):
    f = _store(tmp_path).facets()
    assert f["mappers"] == [
        {"name": "Zed", "count": 2},
        {"name": "Yan", "count": 1},
        {"name": "Yan, Jr", "count": 1},
    ]
    assert f["levels"] == {"Easy": 1, "Normal": 1, "Hard": 1, "Expert": 1, "ExpertPlus": 2}


def test_old_schema_database_is_migrated_in_place(tmp_path):
    path = tmp_path / "old.sqlite"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE maps(id TEXT PRIMARY KEY, folder TEXT, title TEXT, mapper TEXT,"
        " environment TEXT, parse_error TEXT, scanned_at TEXT)"
    )
    db.execute("INSERT INTO maps VALUES('o','o','Old','Zed','E1',NULL,NULL)")
    db.commit()
    db.close()
    s = Store(path)
    rows, total = s.query_maps(level=("Easy",))
    assert (rows, total) == ([], 0)
    assert _ids(s, mapper=("Zed",)) == "o" and s.facets()["levels"]["Easy"] == 0
    s.upsert_map("o", "o", "Old", "Zed", "E1", None, None, None, E)
    assert _ids(s, level=("Easy",)) == "o"


def test_parse_query_scopes_and_validation():
    assert parse_query({"q_fields": "title"}).q_fields == "title"
    assert parse_query({"q_fields": "mapper"}).q_fields == "mapper"
    assert parse_query({"q_fields": "title,mapper"}).q_fields == "name"
    q = parse_query({"mapper": f"A, B{MAPPER_SEP}C", "level": "Easy,Hard", "level_mode": "all"})
    assert q.mapper == ("A, B", "C") and q.level == ("Easy", "Hard") and q.level_mode == "all"
    for bad in ({"level": "Nope"}, {"level_mode": "x"}, {"mapper": "x" * 201}):
        with pytest.raises(ValueError):
            parse_query(bad)


@given(st.lists(st.text(max_size=12), max_size=8))
def test_level_mask_ignores_unknown_and_roundtrips(names):
    mask = level_mask(names)
    assert mask < 32
    assert {n for i, n in enumerate(LEVEL_NAMES) if mask >> i & 1} == set(names) & set(LEVEL_NAMES)


@given(st.text(max_size=30))
def test_hostile_mapper_values_never_break_the_query(tmp_path_factory, value):
    s = Store(tmp_path_factory.mktemp("h") / "db.sqlite")
    s.upsert_map("a", "a", "A", "Zed", "E1", None)
    rows, total = s.query_maps(mapper=(value,))
    assert total == len(rows) == (1 if value == "Zed" else 0)


def test_http_filters_and_facets(svc, client):
    svc.store.upsert_map("zz", "zz", "Z", "A, B", "E9", None, None, None, E)
    r = client.get("/api/maps", params=[("mapper", "A, B"), ("level", "Easy")]).json()
    assert [i["id"] for i in r["items"]] == ["zz"]
    assert client.get("/api/maps?level=Bogus").status_code == 400
    assert client.get("/api/maps?level_mode=maybe").status_code == 400
    f = client.get("/api/maps/facets").json()
    assert {"name": "A, B", "count": 1} in f["mappers"] and f["levels"]["Easy"] >= 1


def test_refresh_fills_levels_from_the_map(svc, client):
    assert sum(client.get("/api/maps/facets").json()["levels"].values()) >= 1
