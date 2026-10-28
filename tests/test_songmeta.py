from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.songmeta import SongMeta, file_meta, parse_title, project_meta


def test_artist_dash_title_with_bracket_part():
    title = "High Roller Penny (DEMO) - Stage 1-1 OST"
    assert parse_title(title, "Chan") == SongMeta("Stage 1-1 OST", "DEMO", "High Roller Penny")


def test_trailing_bracket_goes_to_sub_name():
    assert parse_title("Artist - Song [Official Video]", "") == SongMeta(
        "Song", "Official Video", "Artist"
    )


def test_no_dash_uses_channel_as_author():
    assert parse_title("Just A Song", "Some Channel") == SongMeta("Just A Song", "", "Some Channel")


def test_topic_channel_suffix_is_dropped_and_blank_channel_is_unknown():
    assert parse_title("Song", "Band - Topic").author == "Band"
    assert parse_title("Song", "").author == "Unknown"


def test_dash_inside_a_word_does_not_split():
    assert parse_title("Stage 1-1 OST", "C").song == "Stage 1-1 OST"


def test_title_that_is_only_a_bracket_is_kept():
    assert parse_title("(DEMO)", "C").song == "(DEMO)"


@given(st.text(), st.text())
def test_parse_never_returns_empty_names_or_control_characters(title, channel):
    meta = parse_title(title, channel)
    assert meta.song and meta.author
    for field in (meta.song, meta.sub, meta.author):
        assert len(field) <= 120
        assert field == " ".join(field.split())


def test_file_meta_prefers_tags_then_file_name():
    assert file_meta("my-song.mp3", {"title": "T (Live)", "artist": "Art"}) == SongMeta(
        "T", "Live", "Art"
    )
    assert file_meta("my song.mp3", {}) == SongMeta("my song", "", "Unknown")


def test_en_and_em_dash_also_separate_artist_and_song():
    for dash in (chr(0x2013), chr(0x2014)):
        assert parse_title(f"Artist {dash} Song", "C") == SongMeta("Song", "", "Artist")


def test_project_name_of_the_sample_video_splits_at_the_spaced_dash():
    # beat-analyser drops brackets and writes spaces as underscores in the project name
    got = project_meta("High_Roller_Penny_DEMO_-_Stage_1-1_OST")
    assert got == SongMeta("Stage 1-1 OST", "", "High Roller Penny DEMO")


def test_project_name_that_is_a_video_id_stays_the_song_name():
    assert project_meta("VKUGl7wR7Dg") == SongMeta("VKUGl7wR7Dg", "", "Unknown")


def test_underscored_project_names_become_spaced_titles():
    assert project_meta("_a_b_-_c_d") == SongMeta("c d", "", "a b")
    assert project_meta("_High_Roller_Penny_-_Stage_1-1_OST") == SongMeta(
        "Stage 1-1 OST", "", "High Roller Penny"
    )
    assert project_meta("__just_a_song__") == SongMeta("just a song", "", "Unknown")
    assert project_meta("Stage_1-1_OST").song == "Stage 1-1 OST"


@given(st.text())
def test_project_meta_has_no_underscores_and_no_edge_spaces(name):
    meta = project_meta(name)
    for field in (meta.song, meta.sub, meta.author):
        assert "_" not in field and field == field.strip()
