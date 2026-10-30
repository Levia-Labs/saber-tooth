"""Persisted settings: concurrency cap bounds, game folder validation, survival across reopen."""

import contextlib

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from saber_tooth.settings import SettingError, Settings, clean_game_dir


def game(tmp_path):
    root = tmp_path / "Beat Saber"
    (root / "Beat Saber_Data").mkdir(parents=True)
    return root


def test_the_default_is_one_worker(tmp_path):
    assert Settings(tmp_path / "s.db").max_concurrent_jobs() == 1


def test_a_saved_value_survives_reopening(tmp_path):
    Settings(tmp_path / "s.db").set_max_concurrent_jobs(3, recommended=4)
    assert Settings(tmp_path / "s.db").max_concurrent_jobs() == 3


@pytest.mark.parametrize("bad", [0, -1, 5, True, "2", 2.5, None])
def test_out_of_range_or_non_integer_values_are_refused(tmp_path, bad):
    s = Settings(tmp_path / "s.db")
    with pytest.raises(SettingError):
        s.set_max_concurrent_jobs(bad, recommended=4)
    assert s.max_concurrent_jobs() == 1


def test_the_cap_equal_to_the_recommendation_is_accepted(tmp_path):
    s = Settings(tmp_path / "s.db")
    s.set_max_concurrent_jobs(4, recommended=4)
    assert s.max_concurrent_jobs() == 4


def test_a_corrupt_stored_value_reads_as_the_default(tmp_path):
    s = Settings(tmp_path / "s.db")
    s.put("max_concurrent_jobs", "banana")
    assert s.max_concurrent_jobs() == 1


def test_game_dir_round_trips_and_clears(tmp_path):
    s = Settings(tmp_path / "s.db")
    root = game(tmp_path)
    s.set_game_dir(str(root))
    assert Settings(tmp_path / "s.db").game_dir() == root.resolve()
    s.set_game_dir("")
    assert s.game_dir() is None


@pytest.mark.parametrize(
    "raw",
    ["", "relative/path", "bad\x00path", "x" * 5000, None, 5],
)
def test_clean_game_dir_refuses_unusable_input(tmp_path, raw):
    if raw == "":
        assert clean_game_dir(raw) is None
        return
    with pytest.raises(SettingError):
        clean_game_dir(raw)


def test_a_folder_that_is_not_a_game_install_is_refused(tmp_path):
    (tmp_path / "docs").mkdir()
    with pytest.raises(SettingError, match="Beat Saber"):
        clean_game_dir(str(tmp_path / "docs"))


def test_a_missing_folder_is_refused(tmp_path):
    with pytest.raises(SettingError, match="not a folder"):
        clean_game_dir(str(tmp_path / "nope"))


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=60)
@given(st.one_of(st.text(max_size=300), st.integers(), st.none(), st.binary(max_size=20)))
def test_clean_game_dir_only_ever_raises_setting_error(raw):
    with contextlib.suppress(SettingError):
        clean_game_dir(raw)
