# ruff: noqa: F811
"""After a map operation only its chain (original and copies) is re-indexed, never the library."""

import shutil
import time

import pytest

from saber_tooth.copynames import chain_names
from saber_tooth.service import Service, map_id_for
from tests.crop_helpers import cuts  # noqa: F401
from tests.test_fix_map import CLASH
from tests.test_service import NAME, _make

COPY = f"{NAME} [saber-tooth]"
OTHERS = 200


def _fail_full(*_a, **_k):
    raise AssertionError("full library refresh on an operation path")


@pytest.fixture
def lib(tmp_path, monkeypatch):
    """A library of OTHERS unrelated maps plus the fixture map; spies on the indexer."""
    svc = _make(tmp_path, extra=CLASH)
    for i in range(OTHERS):
        shutil.copytree(svc.levels / NAME, svc.levels / f"Other {i:03d}")
    svc.refresh_library()
    indexed: list[str] = []
    timing = {"s": 0.0}
    real_index = Service._index_folder
    real_chain = Service.reindex_chain

    def spy(self, folder, pending):
        indexed.append(folder.name)
        return real_index(self, folder, pending)

    def timed(self, *a, **k):
        t = time.perf_counter()
        try:
            return real_chain(self, *a, **k)
        finally:
            timing["s"] += time.perf_counter() - t

    monkeypatch.setattr(Service, "_index_folder", spy)
    monkeypatch.setattr(Service, "reindex_chain", timed)
    monkeypatch.setattr(Service, "refresh_library", _fail_full)
    svc.indexed, svc.timing = indexed, timing
    return svc


def test_chain_names_property():
    listing = [NAME, COPY, "Other", "Other [saber-tooth]"]
    assert chain_names(listing, [NAME]) == sorted([NAME, COPY])
    assert chain_names(listing, ["Gone"]) == ["Gone"]


def _only_chain(svc, chain):
    assert svc.indexed and set(svc.indexed) <= set(chain), svc.indexed
    assert svc.timing["s"] < 1.0


def test_rename_reindexes_only_the_chain(lib):
    svc = lib
    shutil.copytree(svc.levels / NAME, svc.levels / COPY)
    svc.reindex_folders([COPY])
    svc.indexed.clear()
    svc.timing["s"] = 0.0
    new_id = svc.rename_map(map_id_for(NAME), "Renamed")
    assert new_id == map_id_for("Renamed")
    _only_chain(svc, ["Renamed", "Renamed [saber-tooth]", NAME, COPY])
    ids = {m["id"] for m in svc.store.list_maps()}
    assert new_id in ids and map_id_for(NAME) not in ids and map_id_for(COPY) not in ids
    assert map_id_for("Renamed [saber-tooth]") in ids
    assert len(ids) == OTHERS + 2


def test_rename_keep_folder_reindexes_only_the_map(lib):
    lib.rename_map(map_id_for(NAME), "Else", keep_folder=True)
    _only_chain(lib, [NAME])


def test_fix_save_reindexes_only_the_chain(lib):
    report = lib.fix_map(map_id_for(NAME))
    _only_chain(lib, [NAME, report["folder"]])
    assert map_id_for(report["folder"]) in {m["id"] for m in lib.store.list_maps()}


def test_crop_save_reindexes_only_the_chain(lib, cuts):
    from saber_tooth.service.crop import crop_map

    out = crop_map(lib, map_id_for(NAME), 0.0, 8.0)
    _only_chain(lib, [NAME, out["folder"]])
    assert out["cropped_id"] in {m["id"] for m in lib.store.list_maps()}
