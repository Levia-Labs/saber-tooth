import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.beatsaver.cache import BsCache
from saber_tooth.beatsaver.client import BeatSaverError
from saber_tooth.beatsaver.filters import LocalFilter, ServerQuery
from saber_tooth.beatsaver.models import BsDiff, BsMap
from saber_tooth.beatsaver.search import parse_cursor, search


def build_map(mid="a1", diffs=(), score=0.97) -> BsMap:
    return BsMap(
        mid, mid, "Song", "", "Artist", "Mapper", 120.0, 200, score, 10, 0, (), False,
        mid * 4, "https://r2cdn.beatsaver.com/x.zip", "", "",
        tuple(BsDiff(c, d, n, 10.0, 100, 100.0) for c, d, n in diffs), "",
    )  # fmt: skip


@pytest.fixture
def make_map():
    return build_map


class FakeClient:
    def __init__(self, pages: list[list[BsMap]], fail_from: int | None = None) -> None:
        self.pages, self.fail_from, self.calls = pages, fail_from, []

    def search(self, params, page):
        self.calls.append(page)
        if self.fail_from is not None and page >= self.fail_from:
            raise BeatSaverError("BeatSaver rate limited", retry_after=7.0)
        return self.pages[page] if page < len(self.pages) else []


@pytest.fixture
def cache(tmp_path):
    return BsCache(tmp_path / "db.sqlite")


@pytest.fixture
def fake_client_with_pages():
    plain = [("Standard", "Normal", 1.0)]
    pages = [[build_map(f"p{p}m{i}", plain) for i in range(3)] for p in range(3)]
    pages.append([build_map("hit", [("Standard", "Easy", 1.0)])])
    return FakeClient(pages)


def test_requires_standard_characteristic(make_map):
    m = make_map(
        diffs=[("OneSaber", "Easy", 1.5), ("OneSaber", "Normal", 1.5), ("OneSaber", "Hard", 1.5)]
    )
    f = LocalFilter(diffs=frozenset({"Easy", "Normal", "Hard"}))
    assert not f.matches(m)


def test_nps_scope_any(make_map):
    m = make_map(
        diffs=[("Standard", "Easy", 0.8), ("Standard", "Normal", 1.4), ("Standard", "Hard", 2.6)]
    )
    assert LocalFilter(nps_min=1, nps_max=2, nps_scope="any").matches(m)
    assert not LocalFilter(nps_min=1, nps_max=2, nps_scope="all").matches(m)


def test_nps_ignores_other_characteristics_and_bounds_inclusive(make_map):
    m = make_map(diffs=[("Standard", "Easy", 2.0), ("OneSaber", "Easy", 1.5)])
    assert LocalFilter(nps_min=2, nps_max=2).matches(m)
    assert not LocalFilter(nps_min=1.4, nps_max=1.6).matches(m)
    assert not LocalFilter(nps_min=1).matches(make_map(diffs=[("OneSaber", "Easy", 3)]))
    assert not LocalFilter(nps_scope="all", nps_min=0).matches(make_map(diffs=[]))


def test_diffs_any_mode_and_rating(make_map):
    m = make_map(diffs=[("Standard", "Hard", 3.0)], score=0.9)
    assert LocalFilter(diffs=frozenset({"Easy", "Hard"}), diffs_mode="any").matches(m)
    assert not LocalFilter(diffs=frozenset({"Easy", "Hard"})).matches(m)
    assert not LocalFilter(min_rating=0.95).matches(m)
    assert LocalFilter(min_rating=0.9).matches(m)
    assert LocalFilter().matches(make_map())


def test_to_params_never_sends_min_nps():
    q = ServerQuery(tags=("rock", "metal"), min_rating=0.95, ranked=True, nps_max=2)
    p = q.to_params()
    assert p["tags"] == "rock|metal" and p["minRating"] == "0.95" and p["leaderboard"] == "Ranked"
    assert "minNps" not in p and "maxNps" not in p and p["ascending"] == "false"
    all_scope = ServerQuery(nps_max=2, nps_scope="all", full_spread=True).to_params()
    assert all_scope["maxNps"] == "2" and all_scope["fullSpread"] == "true"
    assert "minNps" not in all_scope


def test_cursor_advances_past_empty_pages(fake_client_with_pages, cache):
    res = search(
        fake_client_with_pages,
        cache,
        ServerQuery(),
        LocalFilter(diffs=frozenset({"Easy"})),
        cursor=None,
        limit=5,
        max_pages=2,
    )
    assert res.items == [] and res.scanned > 0 and res.cursor == "2.0"
    nxt = search(
        fake_client_with_pages, cache, ServerQuery(), LocalFilter(diffs=frozenset({"Easy"})),
        cursor=res.cursor, limit=5, max_pages=2,
    )  # fmt: skip
    assert [m.id for m in nxt.items] == ["hit"] and nxt.matched == 1 and nxt.cursor == "4.0"


def test_stops_mid_page_and_resumes(cache):
    page = [build_map(f"m{i}", [("Standard", "Easy", 1)]) for i in range(5)]
    client = FakeClient([page])
    first = search(client, cache, ServerQuery(), LocalFilter(), None, limit=2)
    assert [m.id for m in first.items] == ["m0", "m1"] and first.cursor == "0.2"
    second = search(client, cache, ServerQuery(), LocalFilter(), first.cursor, limit=10)
    assert [m.id for m in second.items] == ["m2", "m3", "m4"] and second.cursor is None


def test_query_pages_are_cached(cache):
    client = FakeClient([[build_map("m0")]])
    search(client, cache, ServerQuery(), LocalFilter(), None)
    search(client, cache, ServerQuery(), LocalFilter(), None)
    assert client.calls == [0, 1]  # second run reads page 0 and the empty page 1 from cache
    search(client, cache, ServerQuery(q="other"), LocalFilter(), None)
    assert client.calls[2] == 0


def test_error_after_progress_returns_partial(cache):
    ok = [build_map(f"m{i}", [("Standard", "Easy", 1)]) for i in range(2)]
    client = FakeClient([ok, ok], fail_from=1)
    res = search(client, cache, ServerQuery(), LocalFilter(), None, limit=10)
    assert len(res.items) == 2 and res.cursor == "1.0"
    assert res.partial_reason and res.retry_after == 7.0


def test_error_without_progress_raises(cache):
    with pytest.raises(BeatSaverError):
        search(FakeClient([[]], fail_from=0), cache, ServerQuery(), LocalFilter(), None)


@pytest.mark.parametrize("bad", ["x", "1", "1.", "-1.0", "1.2.3", "1.0 ", chr(0x663) + ".0"])
def test_bad_cursor(bad):
    with pytest.raises(ValueError):
        parse_cursor(bad)


@settings(deadline=None, max_examples=60)
@given(
    sizes=st.lists(st.integers(1, 6), min_size=1, max_size=6),
    limit=st.integers(1, 8),
    max_pages=st.integers(1, 4),
    seed=st.integers(0, 2**16),
)
def test_paging_yields_every_match_exactly_once(tmp_path_factory, sizes, limit, max_pages, seed):
    cache = BsCache(tmp_path_factory.mktemp("c") / "db.sqlite")
    pages, n = [], 0
    for size in sizes:
        row = []
        for _ in range(size):
            n += 1
            hit = (n * 7 + seed) % 3 == 0
            row.append(build_map(f"id{n}", [("Standard", "Easy" if hit else "Hard", 1)]))
        pages.append(row)
    expected = [m.id for row in pages for m in row if any(d.difficulty == "Easy" for d in m.diffs)]
    got, cursor = [], None
    for _ in range(200):
        res = search(
            FakeClient(pages), cache, ServerQuery(), LocalFilter(diffs=frozenset({"Easy"})),
            cursor, limit=limit, max_pages=max_pages,
        )  # fmt: skip
        got += [m.id for m in res.items]
        cursor = res.cursor
        if cursor is None:
            break
    assert cursor is None and got == expected
