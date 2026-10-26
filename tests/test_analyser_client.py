import json

import httpx
import pytest

from saber_tooth.analyser_client import AnalyserClient, AnalyserError


def _project(uploads, name="song"):
    folder = uploads / name
    folder.mkdir(parents=True)
    meta = {"name": name, "key": "C", "bpm": 120}
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (folder / "beats.csv").write_text("0.5\n1.0\n", encoding="utf-8")


def _client(tmp_path, handler):
    return AnalyserClient("http://analyser", tmp_path, httpx.MockTransport(handler))


def _zip_response(name):
    headers = {"Content-Disposition": f'attachment; filename="{name}_tracks.zip"'}
    return httpx.Response(200, content=b"zip", headers=headers)


def test_analyse_url_reads_project(tmp_path):
    _project(tmp_path, "abc123")
    seen = []

    def handler(request):
        seen.append(request)
        return _zip_response("abc123")

    result = _client(tmp_path, handler).analyse_url("https://youtu.be/abc123")
    assert result.name == "abc123"
    assert result.beats == [0.5, 1.0]
    assert "origin" not in seen[0].headers
    assert json.loads(seen[0].content) == {"url": "https://youtu.be/abc123"}


def test_analyse_file_uploads(tmp_path):
    _project(tmp_path)
    wav = tmp_path / "in.wav"
    wav.write_bytes(b"RIFF")
    seen = []

    def handler(request):
        seen.append(request)
        return _zip_response("song")

    result = _client(tmp_path, handler).analyse_file(wav, "song.wav")
    assert result.bpm == 120
    assert seen[0].url.path == "/upload"
    assert "origin" not in seen[0].headers


def test_error_json_becomes_analyser_error(tmp_path):
    def handler(request):
        return httpx.Response(400, json={"error": "too long"})

    with pytest.raises(AnalyserError, match="too long"):
        _client(tmp_path, handler).analyse_url("u")


def test_error_without_json(tmp_path):
    def handler(request):
        return httpx.Response(502, content=b"bad gateway")

    with pytest.raises(AnalyserError, match="502"):
        _client(tmp_path, handler).analyse_url("u")


def test_transport_failure_wrapped(tmp_path):
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(AnalyserError, match="unreachable"):
        _client(tmp_path, handler).analyse_url("u")


@pytest.mark.parametrize(
    "disposition",
    [
        'attachment; filename="../evil_tracks.zip"',
        'attachment; filename="a/b_tracks.zip"',
        'attachment; filename="a\\b_tracks.zip"',
        'attachment; filename="_tracks.zip"',
        'attachment; filename="..\\..\\x_tracks.zip"',
        'attachment; filename="song.zip"',
        "attachment",
        "",
    ],
)
def test_unsafe_project_name_rejected(tmp_path, disposition):
    def handler(request):
        return httpx.Response(200, content=b"z", headers={"Content-Disposition": disposition})

    with pytest.raises(AnalyserError):
        _client(tmp_path, handler).analyse_url("u")
