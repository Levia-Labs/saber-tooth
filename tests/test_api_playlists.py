import base64
import json

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.beatsaver.playlists import BadSubfolder, build_doc, target_dir, write_bplist
from saber_tooth.playlists.songcore import songcore_hash
from tests.test_service import NAME, _make

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


@pytest.fixture
def out(tmp_path):
    d = tmp_path / "Playlists"
    d.mkdir()
    return d


@pytest.fixture
def client(svc, out):
    with TestClient(create_app(svc, playlists_dir=out), base_url="http://localhost") as c:
        yield c


def _mid(client):
    return client.get("/api/maps").json()["items"][0]["id"]


def test_schema_and_subfolder(tmp_path):
    doc = build_doc("T", [{"hash": "A" * 40, "songName": "s", "levelAuthorName": "m"}],
                    author="me", description="d", cover=b"x", sync_url="http://h/x")  # fmt: skip
    assert doc["playlistTitle"] == "T" and doc["playlistAuthor"] == "me"
    assert doc["image"].startswith("base64,") and doc["customData"] == {"syncURL": "http://h/x"}
    assert doc["songs"][0]["hash"] == "A" * 40
    path = write_bplist(doc, tmp_path, "saber-tooth/sub")
    assert path.parent == (tmp_path / "saber-tooth" / "sub").resolve()
    assert json.loads(path.read_text(encoding="utf-8"))["playlistTitle"] == "T"


@pytest.mark.parametrize(
    "sub",
    ["..", "../x", "a/../../x", "/abs", "C:\\x", "a\\..\\..", "con", "a/b/c/d", "x:y", "a."],
)
def test_traversal_rejected(tmp_path, sub):
    with pytest.raises(BadSubfolder):
        target_dir(tmp_path, sub)
    assert not (tmp_path.parent / "x").exists()


def test_create_hash_missing_and_rewrite(client, svc):
    mid = _mid(client)
    made = client.post("/api/playlists", json={
        "title": "Mine", "songs": [{"map_id": mid}, {"hash": "B" * 40, "song_name": "Gone"}],
        "cover": {"data": base64.b64encode(PNG).decode()},
    }).json()  # fmt: skip
    assert made["songs_count"] == 2 and made["missing_count"] == 1 and made["cover_url"]
    songs = made["songs"]
    folder = svc.levels / client.get(f"/api/maps/{mid}").json()["folder"]
    assert songs[0]["hash"] == songcore_hash(folder) and not songs[0]["missing"]
    assert songs[1]["missing"]
    # rewriting a difficulty file changes the hash at the next read
    diff = next(p for p in folder.glob("*.dat") if p.name.lower() != "info.dat")
    diff.write_bytes(diff.read_bytes() + b" ")
    again = client.get(f"/api/playlists/{made['id']}").json()
    assert again["songs"][0]["hash"] != songs[0]["hash"]
    assert client.get(f"/api/playlists/{made['id']}/cover").content == PNG


def test_validation_and_delete(client):
    assert client.post("/api/playlists", json={"title": ""}).status_code == 400
    bad = {"title": "x", "songs": [{"hash": "zz"}]}
    assert client.post("/api/playlists", json=bad).status_code == 400
    bad = {"title": "x", "cover": {"data": base64.b64encode(b"nope").decode()}}
    assert client.post("/api/playlists", json=bad).status_code == 400
    assert client.post("/api/playlists", json={"title": "x", "songs": [{"map_id": "0" * 12}]}
                       ).status_code == 404  # fmt: skip
    pid = client.post("/api/playlists", json={"title": "x"}).json()["id"]
    assert client.get("/api/playlists").json()["items"][0]["id"] == pid
    assert client.delete(f"/api/playlists/{pid}").status_code == 200
    assert client.get(f"/api/playlists/{pid}").status_code == 404
    assert client.get("/api/playlists/..%2f..").status_code == 404


def test_from_maps_export_subfolder_and_sync(client, out):
    mid = _mid(client)
    res = client.post("/api/playlists/from-maps", json={
        "title": "Gen", "map_ids": [mid], "export": True, "folder": "saber-tooth", "sync": True,
    })  # fmt: skip
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["relative"] == "saber-tooth/Gen.bplist"
    doc = json.loads((out / "saber-tooth" / "Gen.bplist").read_text(encoding="utf-8"))
    pid = body["playlist"]["id"]
    assert doc["customData"]["syncURL"] == f"http://localhost/api/playlists/{pid}/bplist"
    live = client.get(f"/api/playlists/{pid}/bplist").json()
    assert live["songs"] == doc["songs"] and len(doc["songs"]) == 1
    again = client.post(f"/api/playlists/{pid}/export", json={})
    assert again.json()["relative"] == "saber-tooth/Gen.bplist"  # rewritten in place
    escape = client.post(f"/api/playlists/{pid}/export", json={"subfolder": "../x"})
    assert escape.status_code == 400
    assert client.post("/api/playlists/from-maps", json={"title": "e"}).status_code == 400


def test_live_routes_and_export_disabled(client, svc):
    doc = client.get("/api/playlists/live/latest-fixed.bplist")
    assert doc.status_code == 200 and doc.json()["songs"] == []
    assert doc.json()["customData"]["syncURL"].endswith("/live/latest-fixed.bplist")
    assert client.get("/api/playlists/live/latest-generated.bplist").status_code == 200
    assert client.get("/api/playlists/live/nope.bplist").status_code == 404
    assert client.get("/api/playlists/config").json()["export_enabled"] is True
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        pid = c.post("/api/playlists", json={"title": "x"}).json()["id"]
        assert c.post(f"/api/playlists/{pid}/export", json={}).status_code == 404


def test_spa_routes(client):
    assert client.get("/playlists").status_code == 200
    assert client.get("/vr/playlists").status_code == 200


def test_name_unused():
    assert NAME


def test_picks(client, svc):
    assert client.get("/api/playlists/picks/live/latest-fixed").json() == {"items": []}
    assert client.get("/api/playlists/picks/live/nope").status_code == 404
    assert client.get("/api/playlists/picks/jobs/" + "0" * 32).status_code == 404
    mid = _mid(client)
    jid = svc.store.create_job("generate")
    svc.store.update_job(jid, "done", result={"map_id": mid, "folder": "x"})
    got = client.get(f"/api/playlists/picks/jobs/{jid}").json()["items"]
    assert [i["map_id"] for i in got] == [mid]
    live = client.get("/api/playlists/picks/live/latest-generated").json()["items"]
    assert [i["map_id"] for i in live] == [mid]
    made = client.post("/api/playlists/from-maps", json={"title": "J", "job_id": jid}).json()
    assert made["playlist"]["songs_count"] == 1
