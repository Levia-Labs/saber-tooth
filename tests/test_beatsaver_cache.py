import json
import sqlite3
from pathlib import Path

from saber_tooth.beatsaver.cache import MAP_TTL, QUERY_TTL, BsCache
from saber_tooth.beatsaver.models import BsMap
from saber_tooth.store import Store

FIX = Path(__file__).parent / "fixtures" / "beatsaver"


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


def sample() -> list[BsMap]:
    docs = json.loads((FIX / "search_page0.json").read_text(encoding="utf-8"))["docs"]
    return [BsMap.from_json(d) for d in docs]


def test_maps_round_trip(tmp_path):
    cache = BsCache(tmp_path / "db.sqlite", Clock())
    maps = sample()
    cache.put_maps(maps)
    got = cache.get_maps(["3a1f4", "3a1f5", "nope"])
    assert got == {m.id: m for m in maps}


def test_map_ttl_expiry(tmp_path):
    clock = Clock()
    cache = BsCache(tmp_path / "db.sqlite", clock)
    cache.put_maps(sample())
    clock.now += MAP_TTL - 1
    assert len(cache.get_maps(["3a1f4"])) == 1
    clock.now += 2
    assert cache.get_maps(["3a1f4"]) == {}
    cache.prune()
    clock.now = 0
    assert cache.get_maps(["3a1f4"]) == {}


def test_put_maps_replaces_and_refreshes(tmp_path):
    clock = Clock()
    cache = BsCache(tmp_path / "db.sqlite", clock)
    m = sample()[0]
    cache.put_maps([m])
    clock.now += MAP_TTL - 5
    cache.put_maps([m])
    clock.now += 10
    assert "3a1f4" in cache.get_maps(["3a1f4"])


def test_query_ttl_and_pages(tmp_path):
    clock = Clock()
    cache = BsCache(tmp_path / "db.sqlite", clock)
    assert cache.get_query("k", 0) is None
    cache.put_query("k", 0, ["a", "b"])
    cache.put_query("k", 1, ["c"])
    assert cache.get_query("k", 0) == ["a", "b"] and cache.get_query("k", 1) == ["c"]
    assert cache.get_query("other", 0) is None
    clock.now += QUERY_TTL + 1
    assert cache.get_query("k", 0) is None


def test_many_ids_exceed_sql_variable_limit(tmp_path):
    cache = BsCache(tmp_path / "db.sqlite", Clock())
    cache.put_maps(sample())
    assert len(cache.get_maps([f"x{i}" for i in range(3000)] + ["3a1f4"])) == 1


def test_corrupt_row_is_skipped(tmp_path):
    db = tmp_path / "db.sqlite"
    cache = BsCache(db, Clock())
    cache.put_maps(sample())
    raw = sqlite3.connect(db)
    raw.execute("UPDATE bs_maps SET json='{bad' WHERE id='3a1f4'")
    raw.commit()
    raw.close()
    assert list(cache.get_maps(["3a1f4", "3a1f5"])) == ["3a1f5"]


def test_migrates_existing_store_database(tmp_path):
    db = tmp_path / "saber-tooth.db"
    store = Store(db)
    store.upsert_map("a" * 12, "Folder", "Title", "Mapper", "Env", None)
    cache = BsCache(db, Clock())
    cache.put_maps(sample())
    assert [m["folder"] for m in store.list_maps()] == ["Folder"]
    tables = {r[0] for r in sqlite3.connect(db).execute("SELECT name FROM sqlite_master")}
    assert {"maps", "bs_maps", "bs_queries"} <= tables
    BsCache(db, Clock())  # reopening keeps the data
    assert len(BsCache(db, Clock()).get_maps(["3a1f4"])) == 1
