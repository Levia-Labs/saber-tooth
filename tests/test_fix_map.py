"""Service.fix_map and the autofix CLI: one-click fix into a new folder."""

import json

from saber_tooth import fixer as fx
from saber_tooth.cli import main
from saber_tooth.model import Color, Cut, Note
from saber_tooth.service import Service, map_id_for
from saber_tooth.service import fix as fix_mod
from tests.test_service import NAME, _hashes, _make

CLASH = [Note(8.0, 1, 1, Color(0), Cut(1)), Note(8.0, 1, 1, Color(1), Cut(1))]


def test_fix_map_writes_a_new_folder_and_leaves_the_original(tmp_path):
    svc: Service = _make(tmp_path, extra=CLASH)
    original = svc.levels / NAME
    before = _hashes(original)
    report = svc.fix_map(map_id_for(NAME))
    assert report["folder"] == f"{NAME} [saber-tooth]"
    assert _hashes(original) == before
    assert (svc.levels / report["folder"]).is_dir()
    assert report["applied"] > 0
    assert report["errors"] == 0
    assert report["unfixed"] == []
    assert set(report) >= {"before", "after", "rounds", "difficulties", "map_id"}


def test_fix_map_on_a_clean_map_writes_nothing(tmp_path):
    svc = _make(tmp_path)
    first = svc.fix_map(map_id_for(NAME))
    again = svc.fix_map(map_id_for(first["folder"]))
    assert again["folder"] is None and again["applied"] == 0


def test_autofix_cli_reports_and_writes_json(tmp_path, capsys):
    svc = _make(tmp_path, extra=CLASH)
    levels, data = tmp_path / "af-levels", tmp_path / "af-data"
    code = main(["autofix", str(svc.levels / NAME), "--levels", str(levels), "--data", str(data)])
    out = capsys.readouterr().out.splitlines()
    assert code == 0 and len(out) <= 20
    assert (levels / f"{NAME} [saber-tooth]").is_dir()
    assert json.loads((data / "autofix-report.json").read_text(encoding="utf-8"))["source"] == NAME


def test_fix_does_not_rename_the_loaded_original(tmp_path, monkeypatch):
    svc: Service = _make(tmp_path, extra=CLASH)
    loaded = []
    real_load, real_fix = svc._load, fix_mod.fix_beatmap

    def spy(folder):
        loaded.append(real_load(folder))
        return loaded[-1]

    def shared_info_fix(original, *args, **kw):
        run = real_fix(original, *args, **kw)
        run.fixed = fx.apply_ops(original, [])  # note-only result: info shared with the original
        return run

    monkeypatch.setattr(svc, "_load", spy)
    monkeypatch.setattr(fix_mod, "fix_beatmap", shared_info_fix)
    assert svc.fix_map(map_id_for(NAME))["applied"] > 0
    assert "[saber-tooth]" not in loaded[0].info.song_name
