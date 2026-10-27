import pytest

from saber_tooth.beatsaver.filters import LocalFilter, ServerQuery
from saber_tooth.beatsaver.params import parse_filters
from saber_tooth.beatsaver.presets import FILTER_KEYS
from tests.test_beatsaver_search import build_map


@pytest.mark.parametrize("raw", ["-1", "1000001", "1.5", "x", "nan", "inf"])
def test_min_upvotes_bounds_rejected(raw):
    with pytest.raises(ValueError, match="min_upvotes"):
        parse_filters({"min_upvotes": raw})


@pytest.mark.parametrize(
    ("raw", "value"), [("0", 0), ("25", 25), ("1000000", 1_000_000), ("3.0", 3)]
)
def test_min_upvotes_parsed_to_server_and_local(raw, value):
    server, local = parse_filters({"min_upvotes": raw})
    assert server.min_upvotes == value and local.min_upvotes == value
    assert server.to_params()["minUpVotes"] == str(value)


def test_min_upvotes_absent_sends_nothing():
    server, local = parse_filters({})
    assert local.min_upvotes is None and "minUpVotes" not in server.to_params()
    assert "minUpVotes" not in ServerQuery().to_params()


def test_local_recheck_uses_upvotes():
    m = build_map()  # 10 upvotes
    assert LocalFilter(min_upvotes=10).matches(m)
    assert not LocalFilter(min_upvotes=11).matches(m)


def test_presets_accept_min_upvotes():
    assert "min_upvotes" in FILTER_KEYS
