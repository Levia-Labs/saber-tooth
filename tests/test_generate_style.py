import json
import shutil
import wave
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from saber_tooth import cli
from saber_tooth.analysis import Analysis
from saber_tooth.api import create_app
from saber_tooth.assemble import assemble_new
from saber_tooth.audio import parse_info
from saber_tooth.cli import main
from saber_tooth.environments import BY_NAME
from saber_tooth.mapio import load_map
from saber_tooth.songmeta import describe
from saber_tooth.style import Style
from tests.test_service import _make


def _wav(path: Path, seconds: int = 2) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000 * seconds)
    return path


def _analysis(audio, bpm, density):
    spb = 60.0 / bpm
    beats = [i * spb for i in range(int(60 / spb))]
    step = max(1, round(4 / density))
    return Analysis("Song", "A", bpm, beats, beats[::2], beats[1::2], beats[::step], audio)


def _copy(wav: Path, egg: Path) -> None:
    shutil.copyfile(wav, egg)


def test_style_is_written_as_info_environment_and_colour_scheme(tmp_path):
    a = _analysis(_wav(tmp_path / "a.wav"), 120, 2)
    style = Style("WeaveEnvironment", {"saber_left": "#ff0000", "obstacle": "#00ff00"})
    assemble_new(a, None, tmp_path / "out", 1, _copy, style=style)
    info = json.loads((tmp_path / "out" / "Info.dat").read_text(encoding="utf-8"))
    assert info["_environmentName"] == "WeaveEnvironment"
    scheme = info["_colorSchemes"][0]["colorScheme"]
    assert scheme["saberAColor"] == {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}
    assert scheme["obstaclesColor"]["g"] == 1.0
    assert scheme["saberBColor"] and scheme["environmentColor1Boost"]
    loaded = load_map(tmp_path / "out")
    assert loaded.info.environment == "WeaveEnvironment" and loaded.info.color_scheme


def test_without_style_the_song_picks_environment_and_palette(tmp_path):
    chosen = {}
    for name, bpm, density in (("slow", 70, 0.5), ("fast", 190, 4)):
        wav = _wav(tmp_path / f"{name}.wav")
        bm = assemble_new(_analysis(wav, bpm, density), None, tmp_path / name, 1, _copy)
        chosen[name] = bm.info.environment
        assert bm.info.environment in BY_NAME and bm.info.color_scheme
    assert chosen["slow"] != chosen["fast"]


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


@pytest.fixture
def client(svc):
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        yield c


def _wait(client, job_id):
    client.app.state.api.jobs.wait(job_id, timeout=120.0)
    return client.get(f"/api/jobs/{job_id}").json()


def test_api_passes_a_checked_style_to_generation(client, svc, monkeypatch):
    seen = []

    def fake(url, progress=None, style=None):
        seen.append(style)
        return {"map_id": "m", "folder": "F"}

    monkeypatch.setattr(svc, "run_generate", fake)
    body = {
        "url": "https://youtu.be/abc",
        "style": {"environment": "NiceEnvironment", "colors": {"saber_left": "#AABBCC"}},
    }
    job = _wait(client, client.post("/api/generate", json=body).json()["job"])
    assert job["status"] == "done"
    assert seen == [Style("NiceEnvironment", {"saber_left": "#aabbcc"})]


@pytest.mark.parametrize(
    "style",
    [
        {"environment": "DefaultEnvironment"},
        {"colors": {"saber_left": "red"}},
        {"colors": {"sky": "#ffffff"}},
        "NiceEnvironment",
        {"environment": "../../x"},
    ],
)
def test_api_refuses_a_bad_style(client, style):
    resp = client.post("/api/generate", json={"url": "https://youtu.be/abc", "style": style})
    assert resp.status_code == 400 and "error" in resp.json()


def test_api_refuses_bad_style_on_upload_and_cleans_up(client, svc):
    files = {"file": ("a.wav", b"RIFF")}
    resp = client.post("/api/generate", files=files, params={"style": "{nope"})
    assert resp.status_code == 400
    resp = client.post(
        "/api/generate", files=files, params={"style": '{"colors": {"x": "#000000"}}'}
    )
    assert resp.status_code == 400
    uploads = svc.data / "uploads"
    assert not uploads.exists() or not any(uploads.iterdir())


def test_cli_sends_the_style():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"job": "j"})

    style = {"environment": "WeaveEnvironment", "colors": {"saber_left": "#112233"}}
    transport = httpx.MockTransport(handler)
    assert cli.gen_url("http://y/t", "http://api:1", transport, style) == "j"
    assert seen["body"] == {"url": "http://y/t", "style": style}


def test_cli_builds_style_from_flags(capsys, monkeypatch):
    sent = {}

    def fake(url, api, transport=None, style=None):
        sent["style"] = style
        return "j"

    monkeypatch.setattr(cli, "gen_url", fake)
    argv = ["gen-url", "http://y", "--environment", "KDAEnvironment", "--color", "env_left=#0A0B0C"]
    assert main(argv) == 0
    assert sent["style"] == {"environment": "KDAEnvironment", "colors": {"env_left": "#0a0b0c"}}
    assert main(["gen-url", "http://y", "--color", "env_left=blue"]) == 1
    assert "error:" in capsys.readouterr().err


def test_wait_job_returns_the_result_and_reports_failure():
    states = iter(
        [{"status": "running"}, {"status": "done", "result": {"map_id": "m", "folder": "F"}}]
    )
    ok = httpx.MockTransport(lambda r: httpx.Response(200, json=next(states)))
    assert cli.wait_job("j", "http://api:1", ok, interval=0) == {"map_id": "m", "folder": "F"}
    bad = httpx.MockTransport(
        lambda r: httpx.Response(200, json={"status": "failed", "error": "x"})
    )
    with pytest.raises(ValueError, match="failed: x"):
        cli.wait_job("j", "http://api:1", bad, interval=0)
    slow = httpx.MockTransport(lambda r: httpx.Response(200, json={"status": "running"}))
    with pytest.raises(ValueError, match="still running"):
        cli.wait_job("j", "http://api:1", slow, timeout=0, interval=0)


def test_cli_environments_lists_the_catalogue(capsys):
    assert main(["environments"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == len(BY_NAME)


def test_describe_a_map_folder(tmp_path, capsys):
    a = _analysis(_wav(tmp_path / "a.wav"), 120, 2)
    assemble_new(a, None, tmp_path / "out", 1, _copy)
    got = describe(tmp_path / "out")
    assert got["title"] == "Song" and got["bpm"] > 0 and set(got) == {
        "title", "artist", "duration", "bpm",
    }  # fmt: skip
    assert main(["songmeta", str(tmp_path / "out")]) == 0
    assert json.loads(capsys.readouterr().out)["title"] == "Song"


def test_songmeta_of_a_missing_path_is_an_error(tmp_path, capsys):
    assert main(["songmeta", str(tmp_path / "nope.mp3")]) == 1
    assert capsys.readouterr().err.startswith("error:")


def test_parse_info_reads_duration_and_tags():
    text = json.dumps({"format": {"duration": "12.5", "tags": {"TITLE": "T", "artist": "A"}}})
    assert parse_info(text) == {"duration": 12.5, "tags": {"title": "T", "artist": "A"}}
    assert parse_info("garbage") == {"duration": None, "tags": {}}
