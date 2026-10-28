import copy
import hashlib
import shutil
from pathlib import Path

import httpx
import pytest

from saber_tooth.analyser_client import AnalyserClient
from saber_tooth.fixer import Flip, Move
from saber_tooth.mapio import load_map, write_map
from saber_tooth.model import Color, Cut, Note
from saber_tooth.service import ApplyConflict, Service, map_id_for
from saber_tooth.store import Store

FIXTURE = Path(__file__).parent / "fixtures" / "maps" / "v2_basic"
NAME = "Basic"
NOTE = Note(1.0, 1, 0, Color(0), Cut(1))


def _fake_encode(wav: Path, egg: Path) -> None:
    shutil.copyfile(wav, egg)


def _build_levels(levels: Path, extra=None, env: str | None = None) -> None:
    folder = levels / NAME
    shutil.copytree(FIXTURE, folder)
    bm = load_map(folder)
    for n in ("Easy", "Normal", "Expert"):
        d = copy.deepcopy(bm.difficulties["Hard"])
        d.name, d.filename = n, f"{n}.dat"
        bm.difficulties[n] = d
    if env:
        bm.info.environment = env
    if extra:
        bm.difficulties["Hard"].notes.extend(extra)
    build = levels.parent / "build"
    write_map(bm, build, folder)
    for old in folder.glob("*.dat"):
        old.unlink()
    for new in build.glob("*.dat"):
        shutil.copyfile(new, folder / new.name)


def _client(tmp_path: Path, handler=None) -> AnalyserClient:
    def down(request):
        raise httpx.ConnectError("down")

    return AnalyserClient("http://analyser", tmp_path / "up", httpx.MockTransport(handler or down))


def _make(tmp_path: Path, extra=None, handler=None, env=None) -> Service:
    levels = tmp_path / "levels"
    levels.mkdir()
    _build_levels(levels, extra, env)
    data = tmp_path / "data"
    data.mkdir()
    svc = Service(levels, data, Store(data / "s.db"), _client(tmp_path, handler), _fake_encode)
    svc.refresh_library()
    return svc


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


@pytest.fixture
def levels(svc):
    return svc.levels


def _hashes(folder: Path) -> dict[str, str]:
    return {
        str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def _propose(svc: Service, mid: str, ops: list, status="approved") -> int:
    p = {
        "rule": "manual",
        "difficulty": "Hard",
        "severity": "warn",
        "summary": "test",
        "ops": [op.to_dict() for op in ops],
        "before": [],
        "after": [],
    }
    pid = svc.store.add_proposals(mid, [p])[0]
    svc.store.set_status(pid, status)
    return pid


def test_apply_twice_creates_numbered_folder(svc, levels):
    mid = map_id_for(NAME)
    before = _hashes(levels / NAME)
    _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    first = svc.apply(mid)
    assert first.name == f"{NAME} [saber-tooth]"
    svc.scan(mid)
    _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    second = svc.apply(mid)
    assert second.name == f"{NAME} [saber-tooth 2]"
    assert (levels / f"{NAME} [saber-tooth]").is_dir()
    assert (levels / f"{NAME} [saber-tooth 2]" / "song.ogg").is_file()
    assert load_map(second).info.song_name == "Basic [saber-tooth]"
    assert _hashes(levels / NAME) == before


def test_conflicting_proposals_abort(tmp_path):
    a = Note(5.0, 0, 0, Color(1), Cut(1))
    b = Note(5.0, 1, 0, Color(0), Cut(1))
    svc = _make(tmp_path, extra=[a, b])
    mid = map_id_for(NAME)
    p1 = _propose(svc, mid, [Move("Hard", a, 2, 2, Cut(1))])
    p2 = _propose(svc, mid, [Move("Hard", b, 2, 2, Cut(1))])
    folders = sorted(p.name for p in svc.levels.iterdir())
    with pytest.raises(ApplyConflict) as exc:
        svc.apply(mid)
    assert exc.value.ids == [p1, p2]
    assert sorted(p.name for p in svc.levels.iterdir()) == folders
    assert [p["status"] for p in svc.store.proposals(mid)] == ["approved", "approved"]


def test_original_untouched(svc, levels):
    mid = map_id_for(NAME)
    before = _hashes(levels / NAME)
    svc.scan(mid)
    _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    svc.apply(mid)
    assert _hashes(levels / NAME) == before


def test_apply_aborts_without_all_difficulties(tmp_path):
    svc = _make(tmp_path)
    shutil.rmtree(svc.levels / NAME)
    shutil.copytree(FIXTURE, svc.levels / NAME)
    mid = map_id_for(NAME)
    _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    folders = sorted(p.name for p in svc.levels.iterdir())
    with pytest.raises(ApplyConflict, match="lacks difficulties"):
        svc.apply(mid)
    assert sorted(p.name for p in svc.levels.iterdir()) == folders


def test_scan_without_analyser_records_no_analysis(svc):
    mid = map_id_for(NAME)
    result = svc.run_scan(mid)
    assert result["map_id"] == mid
    assert result["analysis"] is False
    assert isinstance(result["proposals"], int)


def test_scan_with_analyser_and_rescan_replaces_pending(tmp_path):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(500, json={"error": "boom"})

    svc = _make(tmp_path, handler=handler)
    mid = map_id_for(NAME)
    kept = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))], status="rejected")
    stale = _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))], status="pending")
    svc.scan(mid)
    assert seen and b"%s.ogg" % mid.encode() in seen[0].content
    ids = [p["id"] for p in svc.store.proposals(mid)]
    assert kept in ids and stale not in ids
