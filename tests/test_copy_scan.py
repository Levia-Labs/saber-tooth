# ruff: noqa: F811
"""A saber-tooth copy shows its real status at once: its scan row is stored when it is written."""

import shutil

from saber_tooth.checks import run_checks
from saber_tooth.mapio import load_map
from saber_tooth.service import map_id_for
from tests.bg_helpers import settle
from tests.crop_helpers import cuts  # noqa: F401
from tests.test_fix_map import CLASH
from tests.test_relight import _other
from tests.test_service import NAME, _make

COPY = f"{NAME} [saber-tooth]"


def _row(svc, folder: str):
    return svc.store.scan_info(map_id_for(folder))


def test_fix_stores_the_copys_scan(tmp_path):
    svc = _make(tmp_path, extra=CLASH)
    report = svc.fix_map(map_id_for(NAME))
    row = _row(svc, report["folder"])
    want = run_checks(load_map(svc.levels / report["folder"]))
    assert row is not None and len(row["findings"]) == len(want)


def test_relight_stores_the_copys_scan(tmp_path):
    svc = _make(tmp_path)
    report = svc.relight_map(map_id_for(NAME), _other(svc))
    row = _row(svc, report["folder"])
    assert row is not None
    assert len(row["findings"]) == len(run_checks(load_map(svc.levels / COPY)))


def test_an_existing_copy_without_a_scan_gets_one_when_the_library_is_indexed(tmp_path):
    svc = _make(tmp_path)
    shutil.copytree(svc.levels / NAME, svc.levels / COPY)
    assert _row(svc, COPY) is None
    svc.refresh_library()
    settle(svc)
    assert _row(svc, COPY) is not None
    items = [m for m in svc.store.list_maps() if m["folder"] == COPY]
    assert items  # indexed, with a scan row: not "unscanned"


def test_a_copy_that_was_scanned_keeps_its_scan_on_reindex(tmp_path):
    svc = _make(tmp_path)
    shutil.copytree(svc.levels / NAME, svc.levels / COPY)
    svc.refresh_library()
    settle(svc)
    marker = {"findings": [], "analysis": None}
    svc.store.replace_open_proposals(map_id_for(COPY), [], marker)
    svc.refresh_library()
    assert _row(svc, COPY)["findings"] == []


def test_crop_new_map_and_replace_both_store_a_scan(tmp_path, cuts):
    from tests.crop_helpers import make_service

    svc = make_service(tmp_path)
    mid = map_id_for("Song")
    window = svc.crop_timeline(mid)["lengths"]["60"]["suggestions"][0]
    made = svc.crop_map(mid, window["start_beat"], window["end_beat"])
    assert _row(svc, made["folder"]) is not None
    assert _row(svc, "Song") is None
    svc.crop_map(mid, window["start_beat"], window["end_beat"], replace=True)
    assert _row(svc, "Song") is not None


def test_the_backfill_covers_crop_outputs(tmp_path):
    svc = _make(tmp_path)
    for label in ("[2 min]", "[crop 1m05s]"):
        shutil.copytree(svc.levels / NAME, svc.levels / f"{COPY} {label}")
    svc.refresh_library()
    settle(svc)
    assert _row(svc, f"{COPY} [2 min]") is not None
    assert _row(svc, f"{COPY} [crop 1m05s]") is not None
    assert _row(svc, NAME) is None
