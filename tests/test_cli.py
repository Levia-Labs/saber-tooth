import json
from pathlib import Path

import httpx
import pytest

from saber_tooth import cli, cli_library
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


def _copies_dir(tmp_path):
    import shutil

    for name in ("orig", "orig [saber-tooth]"):
        shutil.copytree(FIX / "v2_basic", tmp_path / name)
    return tmp_path


@pytest.mark.parametrize(("mode", "maps"), [("only", 1), ("exclude", 1), (None, 2)])
def test_survey_copies_filter(tmp_path, monkeypatch, mode, maps):
    seen = []
    real = cli.run_checks
    monkeypatch.setattr(cli, "run_checks", lambda b, *a, **k: seen.append(1) or real(b, *a, **k))
    argv = ["survey", str(_copies_dir(tmp_path))] + (["--copies", mode] if mode else [])
    assert main(argv) == 0
    assert len(seen) == maps


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


def _gen(body, status=200):
    transport = httpx.MockTransport(lambda r: httpx.Response(status, json=body))
    return cli.gen_url("http://y/t", "http://api:1", transport)


def test_gen_url_reads_job_key_with_fallbacks():
    assert _gen({"job": "j1"}) == "j1"
    assert _gen({"job_id": "j2"}) == "j2"


def test_gen_url_non_dict_body_is_error(capsys, monkeypatch):
    with pytest.raises(ValueError, match="unexpected response"):
        _gen(["x"])
    real = cli.gen_url
    bad = httpx.MockTransport(lambda r: httpx.Response(200, json="oops"))
    monkeypatch.setattr(cli, "gen_url", lambda url, api, transport=None: real(url, api, bad))
    assert main(["gen-url", "http://y"]) == 1
    assert capsys.readouterr().err.startswith("error: ")


def test_gen_url_http_error(capsys, monkeypatch):
    def fail(url, api, transport=None):
        raise httpx.ConnectError("no")

    monkeypatch.setattr(cli, "gen_url", fail)
    assert main(["gen-url", "http://y"]) == 1
    assert "error" in capsys.readouterr().err


def test_no_command_exits():
    with pytest.raises(SystemExit):
        main([])


def test_scan_api_posts_and_prints_job(capsys, monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.method, request.url.raw_path.decode()))
        return httpx.Response(200, json={"job": "j9"})

    assert cli.scan_api("abc/def", "http://api:1", httpx.MockTransport(handler)) == "j9"
    assert seen == [("POST", "/api/maps/abc%2Fdef/scan")]
    real = cli.scan_api
    bad = httpx.MockTransport(lambda r: httpx.Response(200, json=[1]))
    monkeypatch.setattr(cli, "scan_api", lambda m, a: real(m, a, bad))
    assert main(["scan-api", "abc"]) == 1
    assert capsys.readouterr().err.startswith("error: ")


def test_survey_mapper_filter(capsys):
    assert main(["survey", str(FIX), "--mapper", "nobody-at-all"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["parse_errors=0"]


def _jobs_transport(pages):
    it = iter(pages)
    last = {}

    def handler(request):
        nonlocal last
        last = next(it, last)
        return httpx.Response(200, json=last)

    return httpx.MockTransport(handler)


def _job(status, kind="fix", **kw):
    return {"kind": kind, "status": status, "title": "T", "map_id": "m", "error": None, **kw}


def _wait(pages, **kw):
    lines = []
    code = cli_library.jobs_wait(
        "http://api:1",
        transport=_jobs_transport(pages),
        sleep=lambda s: None,
        out=lines.append,
        **kw,
    )
    return code, lines


def test_jobs_wait_prints_only_on_change_and_succeeds():
    busy = {"running": [_job("running")], "queued": [_job("queued")], "recent": []}
    mid = {"running": [_job("running")], "queued": [], "recent": [_job("done")]}
    end = {"running": [], "queued": [], "recent": [_job("done"), _job("done")]}
    code, lines = _wait([busy, busy, mid, end])
    assert code == 0
    assert lines == [
        "queued 1 running 1 done 0 failed 0",
        "queued 0 running 1 done 1 failed 0",
        "queued 0 running 0 done 2 failed 0",
        "total 2 queued 0 running 0 done 2 failed 0",
    ]


def test_jobs_wait_failure_lists_errors_capped_and_filters_kind():
    bad = [_job("failed", title=f"M{i}", error="boom") for i in range(12)]
    page = {"running": [], "queued": [], "recent": [*bad, _job("done", kind="scan")]}
    code, lines = _wait([page], kind="fix")
    assert code == 1
    assert lines[1] == "failed M0: boom"
    assert len(lines) <= 10 and lines[-2] == "... 5 more failed"
    assert lines[-1] == "total 12 queued 0 running 0 done 0 failed 12"


def test_jobs_wait_timeout_exits_3():
    busy = {"running": [_job("running")], "queued": [], "recent": []}
    t = iter(range(100))
    lines = []
    code = cli_library.jobs_wait(
        "http://api:1",
        poll=1,
        timeout=3,
        transport=_jobs_transport([busy]),
        sleep=lambda s: None,
        clock=lambda: next(t),
        out=lines.append,
    )
    assert code == 3 and lines[-1].startswith("timeout after 3s")


def _maps_transport(n):
    items = [
        {"id": f"id{i}", "folder": f"M{i}", "warnings": 1, "fixed_copy_id": "c" if i == 0 else None}
        for i in range(n)
    ]

    def handler(request):
        if request.url.path == "/api/maps":
            off = int(request.url.params["offset"])
            return httpx.Response(200, json={"items": items[off : off + 100], "total": n})
        found = [
            {"rule": "b", "unfixed_reason": None},
            {"rule": "a", "unfixed_reason": "no verified fix"},
            {"rule": "b", "unfixed_reason": None},
        ]
        return httpx.Response(200, json={"findings": found})

    return httpx.MockTransport(handler)


def test_map_lines_format_and_hidden_original():
    rows = cli_library.map_lines("http://x", _maps_transport(2))
    assert rows[0] == "M0 id0 a:1,b:2 reason=no verified fix hidden-original"
    assert rows[1] == "M1 id1 a:1,b:2 reason=no verified fix"


def test_map_lines_flag_unanalysed_maps_and_count_them():
    def handler(request):
        if request.url.path == "/api/maps":
            items = [{"id": f"id{i}", "folder": f"M{i}", "warnings": 1} for i in range(2)]
            return httpx.Response(200, json={"items": items, "total": 2})
        flag = request.url.path.split("/")[3] == "id1"
        found = [{"rule": "a", "unfixed_reason": None}]
        return httpx.Response(200, json={"findings": found, "unanalysed": flag})

    rows = cli_library.map_lines("http://x", httpx.MockTransport(handler))
    assert rows == ["M0 id0 a:1 reason=-", "M1 id1 a:1 reason=- unanalysed", "1 unanalysed"]


def test_map_lines_caps_and_pages():
    rows = cli_library.map_lines("http://x", _maps_transport(130))
    assert len(rows) == 31 and rows[-1] == "... 100 more"
