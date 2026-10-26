import subprocess
from pathlib import Path

import pytest

from saber_tooth import audio


def test_encode_egg_argv(monkeypatch):
    calls = []
    monkeypatch.setattr(audio.subprocess, "run", lambda *a, **k: calls.append((a, k)))
    audio.encode_egg(Path("a.wav"), Path("b.egg"))
    argv = calls[0][0][0]
    assert argv == [
        "ffmpeg", "-y", "-loglevel", "error", "-i", "a.wav",
        "-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", "b.egg",
    ]  # fmt: skip
    assert calls[0][1]["check"] is True
    assert not calls[0][1].get("shell")


def test_missing_ffmpeg(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(audio.subprocess, "run", boom)
    with pytest.raises(audio.AudioError, match="not installed"):
        audio.encode_egg(Path("a.wav"), Path("b.egg"))


def test_ffmpeg_failure(monkeypatch):
    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, "ffmpeg", stderr=b"bad input")

    monkeypatch.setattr(audio.subprocess, "run", boom)
    with pytest.raises(audio.AudioError, match="bad input"):
        audio.encode_egg(Path("a.wav"), Path("b.egg"))
