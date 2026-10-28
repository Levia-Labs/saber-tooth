# ruff: noqa: F811
import pytest

from saber_tooth.audio import AudioError
from saber_tooth.crop.phrases import grid_timing
from saber_tooth.crop.shift import crop_beatmap
from saber_tooth.crop.write import write_cropped
from saber_tooth.mapio import load_map
from saber_tooth.model import DIFFICULTIES
from tests.crop_helpers import cuts, write_original  # noqa: F401


def _prepare(tmp_path):
    levels = tmp_path / "levels"
    levels.mkdir()
    original = write_original(levels)
    bm = load_map(original)
    return levels, original, crop_beatmap(bm, grid_timing(bm), 0.0, 128.0)


def _bytes(folder):
    return {p.name: p.read_bytes() for p in folder.iterdir()}


def test_a_new_playable_folder_is_written_and_the_original_is_untouched(tmp_path, cuts):
    levels, original, cropped = _prepare(tmp_path)
    before = _bytes(original)
    target = write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    assert target.name == "Song [1 min]"
    names = {p.name for p in target.iterdir()}
    assert names == {f"{d}.dat" for d in DIFFICULTIES} | {"Info.dat", "song.ogg", "cover.jpg"}
    assert (target / "song.ogg").read_bytes() == b"cut"
    assert (target / "cover.jpg").read_bytes() == b"jp"
    assert _bytes(original) == before
    assert [p.name for p in levels.iterdir() if p.name.endswith(".partial")] == []


def test_the_cut_gets_the_lead_in_and_the_fades(tmp_path, cuts):
    levels, original, cropped = _prepare(tmp_path)
    write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    # notes start at beat 0: a 2 s lead-in; 128 beats at 120 bpm is 64 s; the last bar is 2 s
    assert cuts == [("song.ogg", "song.ogg", 0.0, 64.0, 2.0, 0.5, 2.0)]


def test_info_has_the_suffix_and_a_preview_inside_the_new_audio(tmp_path, cuts):
    levels, original, cropped = _prepare(tmp_path)
    target = write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    back = load_map(target)
    assert back.info.song_name == "Song [1 min]"
    assert (back.info.preview_start, back.info.preview_duration) == (16.5, 10.0)  # total 66 s
    assert back.info.song_file == "song.ogg" and back.info.cover_file == "cover.jpg"


def test_a_taken_name_gets_a_number_and_never_an_overwrite(tmp_path, cuts):
    levels, original, cropped = _prepare(tmp_path)
    first = write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    second = write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    assert (first.name, second.name) == ("Song [1 min]", "Song [1 min 2]")
    assert (first / "song.ogg").read_bytes() == b"cut"


def test_an_ffmpeg_failure_leaves_no_folder(tmp_path, monkeypatch):
    levels, original, cropped = _prepare(tmp_path)

    def boom(*args):
        raise AudioError("ffmpeg failed: bad input")

    monkeypatch.setattr("saber_tooth.crop.write.cut_egg", boom)
    with pytest.raises(AudioError, match="bad input"):
        write_cropped(levels, original, original / "song.ogg", cropped, "1 min")
    assert sorted(p.name for p in levels.iterdir()) == ["Song"]
