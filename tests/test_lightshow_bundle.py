"""The bundled lightshow set: file format, service fallback order, caching and the info route."""

import gzip
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.lightshow import BUNDLED, Templates, learn, units
from tests.script_loader import load
from tests.test_service import _make

FIX = Path(__file__).parent / "fixtures" / "maps"


@pytest.fixture
def small(tmp_path):
    path = tmp_path / "small.json.gz"
    learn(FIX).save(path)
    return path


def test_gz_and_plain_roundtrip(tmp_path):
    t = learn(FIX)
    t.save(tmp_path / "t.json.gz")
    t.save(tmp_path / "t.json")
    assert (tmp_path / "t.json.gz").read_bytes()[:2] == b"\x1f\x8b"
    assert Templates.load(tmp_path / "t.json.gz") == Templates.load(tmp_path / "t.json") == t


def test_gz_bytes_are_reproducible(tmp_path):
    t = learn(FIX)
    t.save(tmp_path / "a.json.gz")
    t.save(tmp_path / "b.json.gz")
    assert (tmp_path / "a.json.gz").read_bytes() == (tmp_path / "b.json.gz").read_bytes()


def test_bundled_file_is_valid_and_ships():
    assert BUNDLED.is_file()
    with gzip.open(BUNDLED, "rt", encoding="utf-8") as fh:
        head = fh.read(20)
    assert head.startswith('{"units"')
    assert BUNDLED.stat().st_size < 3_000_000


def test_bundled_used_without_learn(tmp_path, small):
    svc = _make(tmp_path)
    svc.bundled = small
    assert svc._templates() is not None
    info = svc.lightshow_info()
    assert info["source"] == "bundled" and info["learned_at"] is None
    assert info["environments"] > 0 and info["units"] > 0


def test_learned_overrides_bundled(tmp_path, small):
    svc = _make(tmp_path)
    svc.bundled = small
    assert svc.lightshow_info()["units"] > 0
    Templates().save(svc.data / "lightshow.json")
    info = svc.lightshow_info()
    assert info["source"] == "learned" and info["units"] == 0 and info["learned_at"]


def test_learn_writes_learned_file(tmp_path, small):
    svc = _make(tmp_path)
    shutil.copytree(FIX, svc.levels, dirs_exist_ok=True)
    svc.bundled = small
    assert svc.learn() > 0
    assert json.loads((svc.data / "lightshow.json").read_text(encoding="utf-8"))["units"]
    assert svc.lightshow_info()["source"] == "learned"


def test_no_bundle_no_templates(tmp_path):
    svc = _make(tmp_path)
    svc.bundled = tmp_path / "missing.json.gz"
    assert svc._templates() is None
    assert svc.lightshow_info()["units"] == 0


def test_repeated_access_does_not_reload(tmp_path, small, monkeypatch):
    svc = _make(tmp_path)
    svc.bundled = small
    calls = []
    real = Templates.load.__func__

    def counting(cls, path):
        calls.append(path)
        return real(cls, path)

    monkeypatch.setattr(Templates, "load", classmethod(counting))
    units._cache.clear()
    first = svc._templates()
    for _ in range(5):
        assert svc._templates() is first
        svc.lightshow_info()
    assert len(calls) == 1


def test_learned_change_reloads(tmp_path, small):
    svc = _make(tmp_path)
    svc.bundled = small
    learned = svc.data / "lightshow.json"
    Templates().save(learned)
    first = svc._templates()
    assert svc._templates() is first
    learn(FIX).save(learned)
    assert svc._templates() is not first and svc._templates().units


def test_api_lightshow_route(tmp_path, small):
    svc = _make(tmp_path)
    svc.bundled = small
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        body = c.get("/api/lightshow").json()
    assert set(body) == {"source", "environments", "units", "learned_at"}
    assert body["source"] == "bundled"


def test_learn_bundle_tool(tmp_path, capsys):
    tool = load("learn_bundle")
    out = tmp_path / "out.json.gz"
    assert tool.main([str(FIX), "--out", str(out)]) == 0
    first = out.read_bytes()
    assert tool.main([str(FIX), "--out", str(out)]) == 0
    assert out.read_bytes() == first
    text = capsys.readouterr().out
    assert "envs=" in text and "units=" in text and f"bytes={len(first)}" in text
    assert Templates.load(out).units


def test_learn_bundle_tool_missing_dir(tmp_path):
    tool = load("learn_bundle")
    assert tool.main([str(tmp_path / "nope"), "--out", str(tmp_path / "o.json.gz")]) == 1
