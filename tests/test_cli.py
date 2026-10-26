import json
from pathlib import Path

import httpx
import pytest

from saber_tooth import cli
from saber_tooth.cli import main

FIX = Path(__file__).parent / "fixtures" / "maps"


def test_check_prints_counts(capsys):
    assert main(["check", str(FIX / "v2_basic")]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1].startswith("total ") and len(out) <= 20


def test_check_json(capsys):
    assert main(["check", str(FIX / "v2_basic"), "--json"]) == 0
    assert isinstance(json.loads(capsys.readouterr().out), list)


def test_check_bad_folder(capsys, tmp_path):
    assert main(["check", str(tmp_path)]) == 1
    assert "error" in capsys.readouterr().err


def test_inspect(capsys):
    assert main(["inspect", str(FIX / "v2_basic")]) == 0
    out = capsys.readouterr().out
    assert "bpm" in out and "notes=" in out and "nps=" in out
    assert len(out.splitlines()) <= 20


def test_survey(capsys):
    assert main(["survey", str(FIX)]) == 0
    assert "parse_errors=" in capsys.readouterr().out


def test_survey_counts_parse_and_other_errors(capsys, tmp_path, monkeypatch):
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "Info.dat").write_text("{", encoding="utf-8")
    (tmp_path / "boom").mkdir()
    real = cli.run_checks

    def explode(beatmap, *a, **k):
        if beatmap.folder_name == "v2_basic":
            raise RuntimeError("x")
        return real(beatmap, *a, **k)

    monkeypatch.setattr(cli, "run_checks", explode)
    real_load = cli.load_map
    monkeypatch.setattr(
        cli,
        "load_map",
        lambda f: real_load(FIX / "v2_basic") if f.name == "boom" else real_load(f),
    )
    assert main(["survey", str(tmp_path)]) == 0
    assert "parse_errors=2" in capsys.readouterr().out


def test_learn(capsys, tmp_path):
    out_json = tmp_path / "t.json"
    assert main(["learn", str(FIX), str(out_json)]) == 0
    assert out_json.exists()
    assert "total units=" in capsys.readouterr().out


def test_learn_caps_lines(capsys, tmp_path, monkeypatch):
    from saber_tooth.lightshow import Templates, Unit

    t = Templates({f"E{i}": [Unit(f"E{i}", "s", 0.5)] for i in range(30)})
    monkeypatch.setattr(cli, "learn", lambda p: t)
    assert main(["learn", str(tmp_path), str(tmp_path / "o.json")]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) <= 20 and "... " in out[-2] and out[-1] == "total units=30"


def test_gen_url_posts_and_returns_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "job1"})

    transport = httpx.MockTransport(handler)
    assert cli.gen_url("http://y/t", "http://api:1", transport) == "job1"
    assert seen == {"url": "http://api:1/api/generate", "body": {"url": "http://y/t"}}


def test_gen_url_http_error(capsys, monkeypatch):
    def fail(url, api, transport=None):
        raise httpx.ConnectError("no")

    monkeypatch.setattr(cli, "gen_url", fail)
    assert main(["gen-url", "http://y"]) == 1
    assert "error" in capsys.readouterr().err


def test_no_command_exits():
    with pytest.raises(SystemExit):
        main([])
