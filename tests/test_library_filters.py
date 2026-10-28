# ruff: noqa: F811
import sqlite3
import struct
from pathlib import Path

import pytest

from saber_tooth.service.duration import map_duration, ogg_duration
from saber_tooth.store import Store
from saber_tooth.store_maps import STATUS_VALUES
from tests.test_api import MID, NAME, client, svc  # noqa: F401


def _ogg(rate: int, samples: int, junk: int = 0) -> bytes:
    ident = b"\x01vorbis" + struct.pack("<IBIiii", 0, 2, rate, 0, 0, 0) + b"\xb8\x01"
    first = b"OggS\x00\x02" + struct.pack("<q", 0) + b"\0" * 12 + bytes([1, len(ident)]) + ident
    last = b"OggS\x00\x04" + struct.pack("<q", samples) + b"\0" * 12 + bytes([1, 3]) + b"abc"
    return first + b"x" * junk + last


def test_ogg_duration_reads_header_and_last_granule(tmp_path):
    path = tmp_path / "a.ogg"
    path.write_bytes(_ogg(44100, 44100 * 90, junk=300_000))
    assert ogg_duration(path) == pytest.approx(90.0)


@pytest.mark.parametrize("blob", [b"", b"OggS", b"not ogg at all" * 10, _ogg(0, 100)])
def test_ogg_duration_rejects_garbage(tmp_path, blob):
    path = tmp_path / "a.ogg"
    path.write_bytes(blob)
    assert ogg_duration(path) is None


def test_refresh_stores_bpm_and_duration_from_audio(svc, client):
    (svc.levels / NAME / "song.ogg").write_bytes(_ogg(48000, 48000 * 12))
    svc._seen = frozenset()
    item = client.get(f"/api/maps/{MID}").json()
    assert item["duration_s"] == pytest.approx(12.0) and item["bpm"] > 0


def test_duration_falls_back_to_last_object_beat(svc, client):
    item = client.get(f"/api/maps/{MID}").json()  # fixture song.ogg is not a real Ogg
    assert item["duration_s"] is not None and item["duration_s"] > 0


def test_duration_prefers_song_duration_and_never_raises(svc):
    from saber_tooth.mapio import load_map

    folder = svc.levels / NAME
    bm = load_map(folder)
    assert map_duration(folder, bm, {"audio": {"songDuration": 77.5}}) == 77.5
    bm.info.song_file = "../../etc/passwd"
    assert map_duration(folder, bm, None) is not None
    bm.info.bpm = 0.0  # Timing rejects it: result is None, not an exception
    assert map_duration(folder, bm, None) is None


def test_sort_bpm_and_duration_put_nulls_last(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.upsert_map("a", "a", "A", "m", "E1", None, 120.0, 30.0)
    store.upsert_map("b", "b", "B", "m", "E1", None, 90.0, None)
    store.upsert_map("c", "c", "C", "m", "E2", None, None, 200.0)
    for sort, order, want in [
        ("bpm", "asc", "bac"), ("bpm", "desc", "abc"),
        ("duration", "asc", "acb"), ("duration", "desc", "cab"),
    ]:  # fmt: skip
        rows, _ = store.query_maps(sort=sort, order=order)
        assert "".join(r["id"] for r in rows) == want


def test_incomplete_status_filter_facet_and_sort(tmp_path):
    from saber_tooth.store_maps import LEVEL_NAMES, level_mask

    store = Store(tmp_path / "db.sqlite")
    store.upsert_map("a", "a", "A", "m", "E1", None, levels=level_mask(LEVEL_NAMES[:3]))
    store.upsert_map("b", "b", "B", "m", "E1", None, levels=level_mask(LEVEL_NAMES))
    store.upsert_map("c", "c", "C", "m", "E1", None)
    store.upsert_map("d", "d", "D", "m", "E1", None, levels=level_mask(LEVEL_NAMES[:2]))
    store.replace_open_proposals("d", [], scan={"findings": [], "analysis": None})
    status = {r["id"]: r["status"] for r in store.query_maps()[0]}
    assert status == {"a": "incomplete", "b": "unscanned", "c": "incomplete", "d": "ok"}
    rows, _ = store.query_maps(status=("incomplete",))
    assert [r["id"] for r in rows] == ["a", "c"]
    assert store.facets()["status"]["incomplete"] == 2
    rows, _ = store.query_maps(sort="status")
    assert [r["id"] for r in rows] == ["a", "c", "b", "d"]


def _pair(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.upsert_map("o", "Song", "Song", "m", "E1", None, levels=31)
    store.upsert_map("c", "Song [saber-tooth]", "Song", "m", "E2", None, levels=31)
    store.upsert_map("x", "Other", "Other", "m", "E1", None, levels=31)
    return store


def test_original_hidden_while_copy_exists(tmp_path):
    store = _pair(tmp_path)
    rows, total = store.query_maps()
    assert {r["id"] for r in rows} == {"x", "c"} and total == 2
    assert store.query_maps(status=("unscanned",))[1] == 2
    assert store.query_maps(env=("E1",))[1] == 1
    f = store.facets()
    assert f["total"] == 2 and f["status"]["unscanned"] == 2
    assert {e["name"]: e["count"] for e in f["environments"]} == {"E1": 1, "E2": 1}
    assert store.get_map("o")["id"] == "o"  # still reachable by id


def test_original_shown_again_after_copy_deleted(tmp_path):
    store = _pair(tmp_path)
    store.delete_map("c")
    rows, total = store.query_maps()
    assert total == 2 and {r["id"] for r in rows} == {"o", "x"}
    assert store.facets()["total"] == 2


def test_reverse_link_on_copy(tmp_path):
    store = _pair(tmp_path)
    copy, orig = store.get_map("c"), store.get_map("o")
    assert (copy["original_id"], copy["original_folder"]) == ("o", "Song")
    assert (orig["original_id"], orig["original_folder"]) == (None, None)
    assert orig["fixed_copy_id"] == "c"


def test_multi_status_env_and_q_fields(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.upsert_map("a", "fold1", "Alpha", "Zed", "E1", None, levels=31)
    store.upsert_map("b", "fold2", "Beta", "Yan", "E2", None, levels=31)
    store.upsert_map("c", "fold3", "Gamma", "", "E2", "broken")
    ids = lambda **kw: [r["id"] for r in store.query_maps(**kw)[0]]  # noqa: E731
    assert ids(status=("unscanned", "unreadable")) == ["a", "b", "c"]
    assert ids(status=("unreadable",)) == ["c"]
    assert ids(env=("E2",)) == ["b", "c"]
    assert ids(env=("E1", "E2"), status=("unscanned",)) == ["a", "b"]
    assert ids(q="fold1") == ["a"] and ids(q="fold1", q_fields="name") == []
    assert ids(q="yan", q_fields="name") == ["b"]
    with pytest.raises(ValueError):
        store.query_maps(status=("nope",))


def test_facets_ignore_filters(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.upsert_map("a", "a", "A", "m", "E1", None, levels=31)
    store.upsert_map("b", "b", "B", "m", "E2", None, levels=31)
    store.upsert_map("c", "c", "C", "m", "E2", None, levels=31)
    f = store.facets()
    assert (
        f["total"] == 3 and f["status"]["unscanned"] == 3 and set(f["status"]) == set(STATUS_VALUES)
    )
    assert f["environments"] == [{"name": "E2", "count": 2}, {"name": "E1", "count": 1}]


def test_job_makes_status_and_job_field(svc, client):
    jid = svc.store.create_job("scan", MID)
    item = client.get(f"/api/maps/{MID}").json()
    assert item["status"] == "queued" and item["job"] == {
        "id": jid,
        "kind": "scan",
        "status": "queued",
    }
    svc.store.update_job(jid, "running")
    assert client.get(f"/api/maps/{MID}").json()["status"] == "scanning"
    assert client.get("/api/maps?status=scanning").json()["total"] == 1
    assert client.get("/api/maps?status=error,warn").json()["total"] == 0
    assert client.get("/api/maps/facets").json()["status"]["scanning"] == 1
    svc.store.update_job(jid, "done")
    item = client.get(f"/api/maps/{MID}").json()
    assert item["status"] == "unscanned" and item["job"] is None
    ajid = svc.store.create_job("apply", MID)
    svc.store.update_job(ajid, "running")
    assert client.get(f"/api/maps/{MID}").json()["status"] == "applying"
    svc.store.update_job(ajid, "done")
    fjid = svc.store.create_job("fix", MID)
    svc.store.update_job(fjid, "running")
    assert client.get(f"/api/maps/{MID}").json()["status"] == "fixing"
    assert client.get("/api/maps?status=fixing").json()["total"] == 1
    assert client.get("/api/maps/facets").json()["status"]["fixing"] == 1


def test_scan_and_apply_jobs_record_map_id(client, svc):
    from tests.test_api import _wait

    jid = client.post(f"/api/maps/{MID}/scan").json()["job"]
    _wait(client, jid)
    assert svc.store.job(jid)["map_id"] == MID


def test_api_env_repeat_comma_facets_and_errors(client):
    assert client.get("/api/maps?env=DefaultEnvironment&env=Other").status_code == 200
    assert client.get("/api/maps?env=A,B,C").status_code == 200
    assert client.get("/api/maps?q_fields=title,mapper&q=zzz").json()["total"] == 0
    assert client.get("/api/maps?q_fields=folder").status_code == 400
    assert client.get("/api/maps?env=" + ",".join(f"e{i}" for i in range(51))).status_code == 400
    facets = client.get("/api/maps/facets").json()
    assert facets["total"] == 1 and sum(e["count"] for e in facets["environments"]) <= 1
    total = (
        client.get("/api/maps?sort=bpm").status_code,
        client.get("/api/maps?sort=duration").status_code,
    )
    assert total == (200, 200)


def test_migrates_old_schema_database(tmp_path: Path):
    path = tmp_path / "old.sqlite"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE maps(id TEXT PRIMARY KEY, folder TEXT, title TEXT, mapper TEXT,"
        " environment TEXT, parse_error TEXT, scanned_at TEXT);"
        "CREATE TABLE jobs(id TEXT PRIMARY KEY, kind TEXT, status TEXT, error TEXT,"
        " result_json TEXT, created_at TEXT, updated_at TEXT);"
        "INSERT INTO maps VALUES('m1','f','T','M','E',NULL,NULL);"
        "INSERT INTO jobs VALUES('j1','scan','done',NULL,NULL,'t','t');"
    )
    db.commit()
    db.close()
    store = Store(path)
    Store(path)  # idempotent on a second open
    assert store.list_maps()[0]["duration_s"] is None
    assert store.job("j1")["map_id"] is None
    jid = store.create_job("scan", "m1")
    assert store.job(jid)["map_id"] == "m1"
    rows, total = store.query_maps()
    assert total == 1 and rows[0]["status"] == "queued"
