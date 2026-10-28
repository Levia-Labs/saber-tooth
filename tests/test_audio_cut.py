import subprocess
from pathlib import Path

import pytest

from saber_tooth import audio


def test_cut_egg_argv_with_a_lead_in(monkeypatch):
    calls = []
    monkeypatch.setattr(audio.subprocess, "run", lambda *a, **k: calls.append((a, k)))
    audio.cut_egg(Path("a.ogg"), Path("b.ogg"), 32.0, 64.0, 1.5, 0.5, 2.0)
    assert calls[0][0][0] == [
        "ffmpeg", "-y", "-loglevel", "error", "-ss", "32.000", "-t", "64.000", "-i", "a.ogg",
        "-af",
        "adelay=1500:all=1,afade=t=in:st=1.500:d=0.500,afade=t=out:st=63.500:d=2.000",
        "-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", "b.ogg",
    ]  # fmt: skip
    assert calls[0][1]["check"] is True and not calls[0][1].get("shell")


def test_cut_egg_argv_without_a_lead_in(monkeypatch):
    calls = []
    monkeypatch.setattr(audio.subprocess, "run", lambda *a, **k: calls.append((a, k)))
    audio.cut_egg(Path("a.ogg"), Path("b.ogg"), 0.0, 64.0, 0.0, 0.5, 2.0)
    argv = calls[0][0][0]
    assert (
        argv[argv.index("-af") + 1] == "afade=t=in:st=0.000:d=0.500,afade=t=out:st=62.000:d=2.000"
    )


def test_cut_egg_reports_a_missing_ffmpeg(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(audio.subprocess, "run", boom)
    with pytest.raises(audio.AudioError, match="not installed"):
        audio.cut_egg(Path("a.ogg"), Path("b.ogg"), 0.0, 60.0, 0.0, 0.5, 2.0)


def test_cut_egg_reports_an_ffmpeg_failure(monkeypatch):
    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, "ffmpeg", stderr=b"bad input")

    monkeypatch.setattr(audio.subprocess, "run", boom)
    with pytest.raises(audio.AudioError, match="bad input"):
        audio.cut_egg(Path("a.ogg"), Path("b.ogg"), 0.0, 60.0, 0.0, 0.5, 2.0)
