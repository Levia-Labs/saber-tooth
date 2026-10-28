import subprocess

from saber_tooth import audio


def test_parse_tags_lowercases_keys_and_survives_junk():
    text = '{"format": {"tags": {"TITLE": "A", "ARTIST": "B", "n": 3}}}'
    assert audio.parse_tags(text) == {"title": "A", "artist": "B"}
    assert audio.parse_tags("not json") == {}
    assert audio.parse_tags('{"format": {}}') == {}


def test_probe_tags_reads_ffprobe_output_without_running_it(monkeypatch, tmp_path):
    def fake_run(argv, **kwargs):
        assert argv[0] == "ffprobe"
        return subprocess.CompletedProcess(argv, 0, b'{"format": {"tags": {"title": "T"}}}', b"")

    monkeypatch.setattr(audio.subprocess, "run", fake_run)
    assert audio.probe_tags(tmp_path / "a.mp3") == {"title": "T"}


def test_probe_tags_is_empty_when_ffprobe_is_missing(monkeypatch, tmp_path):
    def missing(argv, **kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(audio.subprocess, "run", missing)
    assert audio.probe_tags(tmp_path / "a.mp3") == {}
