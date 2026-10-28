"""Tests for the pure parts of scripts/hub.py; no network."""

from hypothesis import given
from hypothesis import strategies as st

from tests.script_loader import load

hub = load("hub")


def test_short_description_within_cap():
    assert 0 < len(hub.SHORT) <= hub.SHORT_LIMIT


def test_page_exists_and_within_cap():
    assert hub.too_long(hub.SHORT, hub.PAGE.read_text(encoding="utf-8")) == ""


@given(st.integers(0, 300), st.integers(0, 30_000))
def test_too_long_matches_caps(short_len, full_len):
    message = hub.too_long("a" * short_len, "b" * full_len)
    assert bool(message) == (short_len > hub.SHORT_LIMIT or full_len > hub.FULL_LIMIT)


def test_drift_reports_each_field():
    live = {"description": "s", "full_description": "f"}
    assert hub.drift(live, "s", "f") == (True, True)
    assert hub.drift(live, "x", "f") == (False, True)
    assert hub.drift(live, "s", "x") == (True, False)
    assert hub.drift({"description": "", "full_description": None}, "s", "f") == (False, False)
