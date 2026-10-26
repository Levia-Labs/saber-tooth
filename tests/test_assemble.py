import dataclasses
import shutil
import wave
from pathlib import Path

import pytest
from PIL import Image

from saber_tooth.analysis import Analysis
from saber_tooth.assemble import assemble_new, folder_name
from saber_tooth.checks import RULES, run_checks
from saber_tooth.lightshow import Templates, Unit
from saber_tooth.mapio import load_map
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import DIFFICULTIES, BasicEvent, ColorScheme


def _wav(path: Path, seconds: int = 2) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000 * seconds)
    return path


def _analysis(audio: Path | None, bpm: float = 120.0, seconds: int = 60) -> Analysis:
    spb = 60.0 / bpm
    beats = [i * spb for i in range(int(seconds / spb))]
    hh = [b + spb / 2 for b in beats]
    return Analysis("AC/DC: Back?In", "A minor", bpm, beats, beats[::2], beats[1::2], hh, audio)


def _copy(wav: Path, egg: Path) -> None:
    shutil.copyfile(wav, egg)


def _templates() -> Templates:
    group = {"b": 1.0, "g": 0, "e": [{"b": 0.0}]}
    units = [
        Unit("EnvA", s, e, [BasicEvent(0.5, 1, 1)], [(0.0, True)], {BOX_KEYS[0]: [group]})
        for s in ("a", "b")
        for e in (0.1, 0.5, 0.9)
    ]
    return Templates({"EnvA": units}, {"EnvA": [ColorScheme("S", {})]})


def test_folder_name_sanitized():
    got = folder_name('AC/DC: Back?In "Black"')
    assert got == "st-acdc-backin-black (ACDC BackIn Black - saber-tooth)"


def test_assemble_writes_five_difficulties(tmp_path):
    a = _analysis(_wav(tmp_path / "a.wav"))
    out = tmp_path / "out"
    bm = assemble_new(a, None, out, 3, _copy)
    loaded = load_map(out)
    assert set(loaded.difficulties) == set(DIFFICULTIES)
    assert (out / "song.egg").is_file()
    cover = out / "cover.png"
    with Image.open(cover) as im:
        assert im.size == (512, 512)
    assert run_checks(loaded, a, rules=set(RULES)) == []
    assert bm.info.environment == "NiceEnvironment"
    assert bm.info.song_name == "AC/DC: Back?In"
    assert bm.info.mapper == "saber-tooth"
    assert bm.info.preview_duration == 10
    assert 0 < bm.info.preview_start < 2


def test_assemble_is_deterministic(tmp_path):
    a = _analysis(_wav(tmp_path / "a.wav"))
    assemble_new(a, None, tmp_path / "o1", 3, _copy)
    assemble_new(a, None, tmp_path / "o2", 3, _copy)
    for name in ("Expert.dat", "Info.dat", "cover.png"):
        assert (tmp_path / "o1" / name).read_bytes() == (tmp_path / "o2" / name).read_bytes()


def test_assemble_applies_lightshow(tmp_path):
    a = _analysis(_wav(tmp_path / "a.wav"))
    bm = assemble_new(a, _templates(), tmp_path / "out", 3, _copy)
    assert bm.info.environment == "EnvA"
    assert all(d.events and d.boosts is not None for d in bm.difficulties.values())
    assert run_checks(load_map(tmp_path / "out"), a, rules=set(RULES)) == []


def test_assemble_requires_audio(tmp_path):
    with pytest.raises(ValueError, match="audio"):
        assemble_new(_analysis(None), None, tmp_path / "out", 1, _copy)


def test_assemble_raises_on_findings(tmp_path, monkeypatch):
    from saber_tooth import assemble
    from saber_tooth.checks.finding import Finding

    bad = [Finding("crossover", "Easy", 1.0, 1.0, "error", "x")]
    monkeypatch.setattr(assemble, "run_checks", lambda *a, **k: bad)
    with pytest.raises(ValueError, match="crossover"):
        assemble_new(_analysis(_wav(tmp_path / "a.wav")), None, tmp_path / "out", 1, _copy)


def test_folder_name_non_ascii_keeps_letters():
    got = folder_name("Bodø Café 東京")
    assert "(Bodø Café 東京 - saber-tooth)" in got
    assert got.startswith("st-bod-cafe (")


def test_folder_name_degenerate_and_capped():
    assert folder_name("--") == "st-untitled (-- - saber-tooth)"
    assert folder_name("???") == "st-untitled (Untitled - saber-tooth)"
    got = folder_name("ab " * 60)
    title = got.split("(", 1)[1].rsplit(" - ", 1)[0]
    assert len(title) <= 80
    assert len(got.split(" (", 1)[0]) <= 3 + 40
    assert folder_name("a\nb\tc.") == "st-a-b-c (a b c - saber-tooth)"


def test_cover_survives_control_and_non_latin(tmp_path):
    a = _analysis(_wav(tmp_path / "a.wav"))
    a = dataclasses.replace(a, name="Bad\nTitle\t東京\x00")
    assemble_new(a, None, tmp_path / "out", 1, _copy)
    assert (tmp_path / "out" / "cover.png").is_file()


def test_failed_encode_leaves_nothing(tmp_path):
    def boom(wav, egg):
        raise RuntimeError("x")

    out = tmp_path / "out"
    with pytest.raises(RuntimeError):
        assemble_new(_analysis(_wav(tmp_path / "a.wav")), None, out, 1, boom)
    assert not out.exists()
    assert not (tmp_path / ".out.partial").exists()


def test_existing_out_refused(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(FileExistsError):
        assemble_new(_analysis(_wav(tmp_path / "a.wav")), None, out, 1, _copy)
    assert not (tmp_path / ".out.partial").exists()


def test_assemble_refuses_analysis_without_onsets(tmp_path):
    a = dataclasses.replace(_analysis(_wav(tmp_path / "a.wav")), kick=[], snare=[], hh=[])
    with pytest.raises(ValueError, match="no onsets"):
        assemble_new(a, None, tmp_path / "out", 1, _copy)
    assert not (tmp_path / "out").exists()
