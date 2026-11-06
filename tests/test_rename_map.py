import json

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from saber_tooth.service.errors import RenameInvalid
from tests.test_service import NAME, _make

MID = map_id_for(NAME)


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


@pytest.fixture
def client(svc):
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        yield c


def _song_name(folder):
    info = next(p for p in folder.iterdir() if p.name.lower() == "info.dat")
    data = json.loads(info.read_text(encoding="utf-8-sig"))
    return data["_songName"] if "_songName" in data else data["song"]["title"]


def test_rename_moves_folder_info_and_store_rows(client, svc):
    svc.store.update_job(svc.store.create_job("scan", MID), "done")
    r = client.patch(f"/api/maps/{MID}", json={"name": "  New Title  "})
    assert r.status_code == 200
    new_id = map_id_for("New Title")
    assert r.json()["id"] == new_id
    assert r.json()["folder"] == "New Title"
    assert not (svc.levels / NAME).exists()
    assert _song_name(svc.levels / "New Title") == "New Title"
    assert svc.store.get_map(MID) is None
    assert svc.store.get_map(new_id) is not None
    assert svc.store._query("SELECT id FROM jobs WHERE map_id=?", (MID,)) == []
    assert len(svc.store._query("SELECT id FROM jobs WHERE map_id=?", (new_id,))) == 1
    assert client.get(f"/api/maps/{new_id}").status_code == 200
    assert client.get(f"/api/maps/{MID}").status_code == 404


def test_rename_moves_scans_and_proposals(client, svc):
    svc.store._db.execute(
        "INSERT INTO scans(map_id, keys_json, analysis, scanned_at) VALUES(?, '[]', NULL, 'now')",
        (MID,),
    )
    svc.store._db.commit()
    new_id = map_id_for("Other")
    assert client.patch(f"/api/maps/{MID}", json={"name": "Other"}).status_code == 200
    assert svc.store.scan_info(MID) is None
    assert svc.store.scan_info(new_id) is not None


def test_rename_sanitises_folder_name(client, svc):
    r = client.patch(f"/api/maps/{MID}", json={"name": 'What? A "Song": 1.'})
    assert r.status_code == 200
    assert r.json()["folder"] == "What A Song 1"
    assert _song_name(svc.levels / "What A Song 1") == 'What? A "Song": 1.'


@pytest.mark.parametrize(
    "body",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 121},
        {"name": "a/b"},
        {"name": "a\\b"},
        {"name": 5},
        {},
        {"name": "???"},
    ],
)
def test_rename_rejects_bad_names(client, svc, body):
    r = client.patch(f"/api/maps/{MID}", json=body)
    assert r.status_code == 422
    assert (svc.levels / NAME).exists()


def test_rename_non_json_is_400(client):
    r = client.patch(f"/api/maps/{MID}", content=b"nope", headers={"content-type": "text/plain"})
    assert r.status_code == 400


def test_rename_target_exists_is_409(client, svc):
    (svc.levels / "Taken").mkdir()
    r = client.patch(f"/api/maps/{MID}", json={"name": "Taken"})
    assert r.status_code == 409
    assert (svc.levels / NAME).exists()
    assert _song_name(svc.levels / NAME) != "Taken"


def test_rename_busy_is_409(client, svc):
    svc.store.create_job("scan", MID)
    assert client.patch(f"/api/maps/{MID}", json={"name": "Busy"}).status_code == 409
    assert (svc.levels / NAME).exists()


def test_rename_unknown_is_404(client):
    assert client.patch("/api/maps/" + "0" * 12, json={"name": "A"}).status_code == 404


def test_rename_same_name_keeps_id(client, svc):
    r = client.patch(f"/api/maps/{MID}", json={"name": NAME})
    assert r.status_code == 200
    assert r.json()["id"] == MID
    assert (svc.levels / NAME).exists()


def _with_copy(svc):
    import shutil

    shutil.copytree(svc.levels / NAME, svc.levels / f"{NAME} [saber-tooth]")
    svc.refresh_library()
    return map_id_for(f"{NAME} [saber-tooth]")


def test_renaming_a_fixed_copy_keeps_the_suffix_and_the_pairing(client, svc):
    cid = _with_copy(svc)
    r = client.patch(f"/api/maps/{cid}", json={"name": "Fresh"})
    assert r.status_code == 200
    assert r.json()["folder"] == "Fresh [saber-tooth]"
    assert r.json()["id"] == map_id_for("Fresh [saber-tooth]")
    assert _song_name(svc.levels / "Fresh [saber-tooth]") == "Fresh"
    assert (svc.levels / "Fresh").is_dir()  # the original follows, so the pair holds
    assert not (svc.levels / NAME).exists()
    assert r.json()["original_folder"] == "Fresh"


def test_renaming_an_original_moves_its_copy_along(client, svc):
    _with_copy(svc)
    r = client.patch(f"/api/maps/{MID}", json={"name": "Fresh"})
    assert r.status_code == 200
    assert (svc.levels / "Fresh [saber-tooth]").is_dir()
    assert not (svc.levels / f"{NAME} [saber-tooth]").exists()
    assert svc.store.get_map(map_id_for("Fresh [saber-tooth]")) is not None


def test_pair_rename_conflicts_when_the_partner_target_exists(client, svc):
    _with_copy(svc)
    (svc.levels / "Fresh [saber-tooth]").mkdir()
    assert client.patch(f"/api/maps/{MID}", json={"name": "Fresh"}).status_code == 409
    assert (svc.levels / NAME).exists()


def test_keep_folder_rename_accepts_a_slash_in_the_title(svc):
    assert svc.rename_map(MID, "AC/DC - Live", keep_folder=True) == MID
    assert (svc.levels / NAME).is_dir()
    assert _song_name(svc.levels / NAME) == "AC/DC - Live"


def test_keep_folder_rename_still_refuses_control_characters_and_empty(svc):
    for bad in ("", "  ", "a\x00b"):
        with pytest.raises(RenameInvalid):
            svc.rename_map(MID, bad, keep_folder=True)


def test_folder_rename_still_refuses_a_slash(svc):
    with pytest.raises(RenameInvalid):
        svc.rename_map(MID, "AC/DC", keep_folder=False)
    assert (svc.levels / NAME).is_dir()
