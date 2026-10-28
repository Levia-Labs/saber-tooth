import json
import shutil
import wave
from pathlib import Path

import httpx
import pytest

from saber_tooth.analyser_client import AnalyserClient
from saber_tooth.mapio import load_map
from saber_tooth.service import Service
from saber_tooth.store import Store

TITLE = "High_Roller_Penny_DEMO_-_Stage_1-1_OST"


def _project(root: Path, name: str = "song1", title: str = TITLE) -> None:
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    with wave.open(str(folder / "audio.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000)
    beats = [i * 0.5 for i in range(120)]
    meta = {"name": title, "key": "A", "bpm": 120}
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (folder / "beats.csv").write_text("\n".join(map(str, beats)), encoding="utf-8")
    for n, part in (("kick", beats[::2]), ("snare", beats[1::2]), ("hh", beats)):
        (folder / f"{n}.csv").write_text("\n".join(map(str, part)), encoding="utf-8")


def _copy(wav: Path, egg: Path) -> None:
    shutil.copyfile(wav, egg)


@pytest.fixture
def svc(tmp_path):
    _project(tmp_path / "up")

    def handler(request):
        headers = {"Content-Disposition": 'attachment; filename="song1_tracks.zip"'}
        return httpx.Response(200, content=b"zip", headers=headers)

    client = AnalyserClient("http://analyser", tmp_path / "up", httpx.MockTransport(handler))
    levels, data = tmp_path / "levels", tmp_path / "data"
    levels.mkdir()
    data.mkdir()
    s = Service(levels, data, Store(data / "s.db"), client, _copy)
    s.probe_tags = lambda path: {}
    return s


def _info(svc, result):
    return load_map(svc.levels / result["folder"]).info


def test_url_generation_writes_a_finished_map_with_video_names(svc):
    result = svc.run_generate("https://www.youtube.com/watch?v=VKUGl7wR7Dg")
    folder = svc.levels / result["folder"]
    bm = load_map(folder)
    assert len(bm.difficulties) == 5 and result["complete"] and result["errors"] == 0
    info = bm.info
    assert (info.song_name, info.sub_name, info.author) == (
        "Stage 1-1 OST",
        "",
        "High Roller Penny DEMO",
    )
    assert (folder / "song.egg").is_file() and (folder / "cover.png").is_file()
    assert any(m["id"] == result["map_id"] for m in svc.store.list_maps())
    assert not list((svc.data / "staging").iterdir())
    assert not [p for p in svc.levels.iterdir() if p.name.startswith(".")]


def test_older_analyser_naming_the_project_by_video_id_keeps_the_id(svc, tmp_path):
    _project(tmp_path / "up", "song1", title="VKUGl7wR7Dg")  # a response without the title
    info = _info(svc, svc.run_generate("https://youtu.be/x"))
    assert (info.song_name, info.sub_name, info.author) == ("VKUGl7wR7Dg", "", "Unknown")


def test_file_uses_tags_then_file_name(svc, tmp_path):
    song = tmp_path / "my-track.mp3"
    song.write_bytes(b"x")
    svc.probe_tags = lambda path: {"title": "Tagged", "artist": "Band"}
    tagged = _info(svc, svc.run_generate(str(song)))
    assert (tagged.song_name, tagged.author) == ("Tagged", "Band")
    svc.probe_tags = lambda path: {}
    plain = _info(svc, svc.run_generate(str(song)))
    assert (plain.song_name, plain.author) == ("my-track", "Unknown")


def test_a_second_generation_gets_a_numbered_folder(svc):
    first = svc.run_generate("https://youtu.be/x")
    second = svc.run_generate("https://youtu.be/x")
    assert first["folder"] != second["folder"] and first["map_id"] != second["map_id"]
    assert len(list(svc.levels.iterdir())) == 2


def test_failure_leaves_no_folder_and_no_staging(svc):
    def boom(wav, egg):
        raise OSError("disk full")

    svc.encode = boom
    with pytest.raises(OSError):
        svc.run_generate("https://youtu.be/x")
    assert list(svc.levels.iterdir()) == []
    assert not list((svc.data / "staging").iterdir())


def test_analyser_failure_leaves_levels_untouched(svc):
    def down(request):
        raise httpx.ConnectError("down")

    svc.client = AnalyserClient("http://analyser", svc.data, httpx.MockTransport(down))
    with pytest.raises(Exception, match="unreachable"):
        svc.run_generate("https://youtu.be/x")
    assert list(svc.levels.iterdir()) == []


def test_the_fix_engine_runs_on_the_new_map_and_its_result_is_written(svc, monkeypatch):
    from saber_tooth.service import generate

    calls = []
    real = generate.fix_beatmap

    def spy(bm, analysis, templates, seed):
        calls.append(sorted(bm.difficulties))
        bm.info.environment = "BigMirrorEnvironment"
        run = real(bm, analysis, templates, seed)
        run.steps.append(object())  # a recorded step makes the result be written back
        return run

    monkeypatch.setattr(generate, "fix_beatmap", spy)
    result = svc.run_generate("https://youtu.be/x")
    assert len(calls) == 1 and len(calls[0]) == 5
    assert _info(svc, result).environment == "BigMirrorEnvironment"
