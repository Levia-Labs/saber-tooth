from saber_tooth.crop.info import crop_info
from tests.crop_helpers import info


def test_song_name_gets_the_label_and_the_preview_lies_inside_the_audio():
    out = crop_info(info(), 66.0, "1 min")
    assert out.song_name == "Song [1 min]"
    assert (out.preview_start, out.preview_duration) == (16.5, 10.0)  # a quarter in, 10 s long


def test_a_short_clip_gets_a_short_preview_from_the_start():
    out = crop_info(info(), 8.0, "1 min")
    assert (out.preview_start, out.preview_duration) == (0.0, 8.0)


def test_a_missing_preview_length_defaults_to_ten_seconds():
    base = info()
    base.preview_duration = 0.0
    assert crop_info(base, 60.0, "2 min").preview_duration == 10.0


def test_the_original_info_is_not_mutated():
    base = info()
    crop_info(base, 66.0, "1 min")
    assert base.song_name == "Song" and base.preview_start == 10.0
