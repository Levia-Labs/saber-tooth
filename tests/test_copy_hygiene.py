"""One fixed copy per map: in-place fix, refresh, plain crop names, regenerate, fix-all chains."""

import shutil

from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.copynames import fixed_name, strip_fixed
from saber_tooth.findings_summary import maps_with_findings
from saber_tooth.mapio import load_map
from saber_tooth.service import map_id_for
from tests.crop_helpers import NAME as CROP_NAME
from tests.crop_helpers import cuts, make_service  # noqa: F401
from tests.test_fix_map import CLASH, NAME, _make
from tests.test_regenerate import SOURCE, _finding, _generated, gen  # noqa: F401

COPY = f"{NAME} [saber-tooth]"


def _folders(svc):
    return sorted(p.name for p in svc.levels.iterdir() if p.is_dir())


def test_name_helpers_never_double_the_suffix():
    assert strip_fixed("F [saber-tooth] [saber-tooth]") == "F"
    assert strip_fixed("F [saber-tooth 2]") == "F"
    assert fixed_name("F [saber-tooth]") == "F [saber-tooth]"
    assert fixed_name("F") == "F [saber-tooth]"


def test_fixing_a_fixed_copy_fixes_it_in_place(tmp_path):
    svc = _make(tmp_path, extra=CLASH)
    (svc.levels / NAME).rename(svc.levels / COPY)
    svc.refresh_library()
    report = svc.fix_map(map_id_for(COPY))
    assert report["applied"] > 0 and report["folder"] == COPY
    assert _folders(svc) == [COPY]
    assert load_map(svc.levels / COPY).info.song_name.count("[saber-tooth]") == 1


def test_fixing_an_original_refreshes_its_existing_copy(tmp_path):
    svc = _make(tmp_path, extra=CLASH)
    first = svc.fix_map(map_id_for(NAME))
    second = svc.fix_map(map_id_for(NAME))
    assert first["folder"] == second["folder"] == COPY
    assert _folders(svc) == sorted([NAME, COPY])


def test_regenerate_deletes_the_fixed_copy(gen):  # noqa: F811
    from saber_tooth.service.regenerate import regenerate_map

    svc = gen
    result = _generated(svc)
    copy = svc.levels / f"{result['folder']} [saber-tooth]"
    shutil.copytree(svc.levels / result["folder"], copy)
    svc.refresh_library()
    regenerate_map(svc, result["map_id"])
    assert not copy.exists()
    assert (svc.levels / result["folder"]).is_dir()


def test_fix_all_queues_one_fix_per_chain(tmp_path):
    svc = _make(tmp_path)
    shutil.copytree(svc.levels / NAME, svc.levels / COPY)
    svc.refresh_library()
    for folder in (NAME, COPY):
        scan = {"findings": [_finding("r1")], "analysis": None}
        svc.store.replace_open_proposals(map_id_for(folder), [], scan)
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        c.app.state.api.jobs._stop.set()
        out = c.post("/api/maps/fix-all").json()
    assert out["count"] == 1


def test_fix_all_skips_an_original_that_has_a_copy(tmp_path):
    svc = _make(tmp_path)
    shutil.copytree(svc.levels / NAME, svc.levels / COPY)
    svc.refresh_library()
    scan = {"findings": [_finding("r1")], "analysis": None}
    svc.store.replace_open_proposals(map_id_for(NAME), [], scan)
    svc.store.replace_open_proposals(map_id_for(COPY), [], {"findings": [], "analysis": None})
    assert map_id_for(NAME) not in maps_with_findings(svc.store)


def test_crop_names_folder_and_song_with_the_suffix_only(tmp_path, cuts):  # noqa: F811
    svc = make_service(tmp_path)
    result = svc.crop_map(map_id_for(CROP_NAME), 2.0, 122.0)
    assert result["folder"] == "Song [saber-tooth]"
    assert load_map(svc.levels / "Song [saber-tooth]").info.song_name == "Song [saber-tooth]"


def test_crop_overwrites_the_existing_copy_and_a_copy_is_cropped_in_place(tmp_path, cuts):  # noqa: F811
    svc = make_service(tmp_path)
    mid = map_id_for(CROP_NAME)
    first = svc.crop_map(mid, 2.0, 122.0)
    copy_id = first["cropped_id"]
    again = svc.crop_map(mid, 2.0, 122.0)
    assert again["folder"] == first["folder"] == "Song [saber-tooth]"
    in_place = svc.crop_map(copy_id, 2.0, 62.0)
    assert in_place["cropped_id"] == copy_id
    assert _folders(svc) == ["Song", "Song [saber-tooth]"]


def _song_name(folder):
    return load_map(folder).info.song_name


def _copy_with_doubled_folder(tmp_path):
    svc = _make(tmp_path)
    doubled = f"{NAME} [saber-tooth] [saber-tooth]"
    shutil.copytree(svc.levels / NAME, svc.levels / doubled)
    svc.refresh_library()
    return svc, doubled


def test_keep_folder_rename_normalises_a_doubled_copy_and_leaves_the_original(tmp_path):
    svc, doubled = _copy_with_doubled_folder(tmp_path)
    new_id = svc.rename_map(map_id_for(doubled), "Fresh Song", keep_folder=True)
    assert new_id == map_id_for(COPY)
    assert _folders(svc) == sorted([NAME, COPY])
    assert _song_name(svc.levels / COPY) == "Fresh Song"
    assert _song_name(svc.levels / NAME) != "Fresh Song"
    assert svc.store.get_map(map_id_for(doubled)) is None


def test_keep_folder_rename_of_an_original_keeps_its_folder(tmp_path):
    svc = _make(tmp_path)
    assert svc.rename_map(map_id_for(NAME), "Fresh Song", keep_folder=True) == map_id_for(NAME)
    assert _folders(svc) == [NAME] and _song_name(svc.levels / NAME) == "Fresh Song"


def test_keep_folder_patch_is_409_when_the_target_exists(tmp_path):
    svc, doubled = _copy_with_doubled_folder(tmp_path)
    shutil.copytree(svc.levels / NAME, svc.levels / COPY)
    svc.refresh_library()
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        r = c.patch(f"/api/maps/{map_id_for(doubled)}", json={"name": "X", "keep_folder": True})
    assert r.status_code == 409
    assert doubled in _folders(svc)


def test_legacy_tags_stripped_and_split():
    from saber_tooth.copynames import split_copy

    assert strip_fixed("F [saber-tooth] [2 min]") == "F"
    assert strip_fixed("F [crop 1-2] [saber-tooth 2]") == "F"
    assert fixed_name("F [saber-tooth] [2 min]") == "F [saber-tooth]"
    assert split_copy("F [saber-tooth] [2 min]") == ("F", 1, 1)
    assert split_copy("F") == ("F", 0, 0)


def test_keep_folder_rename_normalises_a_legacy_tag_folder(tmp_path):
    svc = _make(tmp_path)
    legacy = f"{NAME} [saber-tooth] [2 min]"
    shutil.copytree(svc.levels / NAME, svc.levels / legacy)
    svc.refresh_library()
    new_id = svc.rename_map(map_id_for(legacy), "Fresh Song", keep_folder=True)
    assert new_id == map_id_for(COPY)
    assert _folders(svc) == sorted([NAME, COPY])
