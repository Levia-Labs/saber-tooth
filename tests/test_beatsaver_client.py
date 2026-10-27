import json
from itertools import pairwise
from pathlib import Path

import httpx
import pytest
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.beatsaver.client import BeatSaverClient, BeatSaverError, download_url_ok
from saber_tooth.beatsaver.models import BsMap

AT = chr(64)
FIX = Path(__file__).parent / "fixtures" / "beatsaver"


def fixture(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


class Clock:
    def __init__(self) -> None:
        self.now = 100.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def make(handler, rate: float = 5.0) -> tuple[BeatSaverClient, Clock]:
    clock = Clock()
    client = BeatSaverClient(httpx.MockTransport(handler), rate, clock, clock.sleep)
    return client, clock


def test_search_parses_latest_published_version():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=fixture("search_page0.json"))

    client, _ = make(handler)
    maps = client.search({"q": "neon", "tags": "a|b", "evil": "x"}, 0)
    req = seen[0]
    assert req.url.host == "api.beatsaver.com" and req.url.path == "/search/text/0"
    assert req.url.params["q"] == "neon" and "evil" not in req.url.params
    assert req.headers["user-agent"].startswith("saber-tooth/")
    first, sparse = maps
    assert first.id == "3a1f4" and first.mapper == "pulsewright" and first.score == 0.9712
    assert first.hash == "aabbccddeeff00112233445566778899aabbccdd"
    assert first.download_url.startswith("https://r2cdn.beatsaver.com/")
    assert [(d.characteristic, d.difficulty) for d in first.diffs][:3] == [
        ("Standard", "Easy"), ("Standard", "Normal"), ("Standard", "Hard"),
    ]  # fmt: skip
    assert sparse.song_name == "" and sparse.diffs == () and sparse.tags == ()


def test_map_round_trips_through_dict():
    m = BsMap.from_json(fixture("search_page0.json")["docs"][0])
    assert BsMap.from_dict(json.loads(json.dumps(m.to_dict()))) == m


def test_from_json_tolerates_garbage():
    for bad in ({}, {"versions": "x", "metadata": []}, {"stats": {"score": "high"}, "tags": [1]}):
        m = BsMap.from_json(bad)
        assert m.diffs == () and m.score == 0.0


def test_maps_by_ids_and_playlists():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.startswith("/maps/ids/"):
            return httpx.Response(200, json=fixture("map_detail.json"))
        if path.startswith("/playlists/search/"):
            return httpx.Response(200, json=fixture("playlist_search.json"))
        assert path == "/playlists/id/77/0"
        return httpx.Response(200, json=fixture("playlist_page0.json"))

    client, _ = make(handler)
    assert [m.id for m in client.maps_by_ids(["3a1f4"])] == ["3a1f4"]
    pl = client.playlist_search({"q": "chill"}, 0)[0]
    assert (pl.id, pl.name, pl.owner) == (77, "Chill Electronic", "curator")
    assert (pl.maps_count, pl.max_nps) == (2, 3.1)
    assert [m.id for m in client.playlist_page(77, 0)] == ["3a1f4", "3a1f5"]
    with pytest.raises(ValueError):
        client.maps_by_ids(["../etc"])


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("https://r2cdn.beatsaver.com/a.zip", True),
        ("https://cdn.beatsaver.com/a.zip", True),
        ("http://r2cdn.beatsaver.com/a.zip", False),
        ("https://beatsaver.com/a.zip", False),
        ("https://evilbeatsaver.com/a.zip", False),
        ("https://beatsaver.com.evil.net/a.zip", False),
        ("https://user" + AT + "r2cdn.beatsaver.com/a.zip", False),
        ("https://r2cdn.beatsaver.com:8443/a.zip", False),
        ("https://r2cdn.beatsaver.com\\" + AT + "evil.net/a.zip", False),
        ("file:///etc/passwd", False),
    ],
)
def test_download_host_allowlist(url, ok):
    assert download_url_ok(url) is ok


@given(st.text(max_size=60))
def test_download_url_never_accepts_foreign_hosts(tail):
    url = "https://example.org/" + tail
    assert not download_url_ok(url)


def test_download_refuses_bad_host_without_request(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    client, _ = make(handler)
    for url in ("http://r2cdn.beatsaver.com/a.zip", "https://evil.example/a.zip"):
        with pytest.raises(BeatSaverError):
            client.download(url, tmp_path / "a.zip", 1000)


def test_redirect_to_foreign_host_is_refused(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://evil.example/a.zip"})

    client, _ = make(handler)
    with pytest.raises(BeatSaverError):
        client.download("https://r2cdn.beatsaver.com/a.zip", tmp_path / "a.zip", 1000)


def test_download_writes_file(tmp_path):
    client, _ = make(lambda r: httpx.Response(200, content=b"zipdata"))
    dest = client.download("https://r2cdn.beatsaver.com/a.zip", tmp_path / "a.zip", 1000)
    assert dest.read_bytes() == b"zipdata"


def test_download_aborts_over_max_bytes(tmp_path):
    client, _ = make(lambda r: httpx.Response(200, content=b"x" * 5000))
    dest = tmp_path / "a.zip"
    with pytest.raises(BeatSaverError, match="too large"):
        client.download("https://r2cdn.beatsaver.com/a.zip", dest, 1000)
    assert not dest.exists()


def test_429_retry_after_retries_then_succeeds():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) <= 2:
            return httpx.Response(429, headers={"retry-after": "2"})
        return httpx.Response(200, json={"docs": []})

    client, clock = make(handler)
    assert client.search({}, 0) == []
    assert len(calls) == 3 and clock.slept.count(2.0) == 2


def test_gives_up_after_four_retries_with_hint():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(429, headers={"retry-after": "500"})

    client, clock = make(handler)
    with pytest.raises(BeatSaverError) as info:
        client.search({}, 0)
    assert len(calls) == 5 and info.value.retry_after == 60.0 and max(clock.slept) == 60.0


def test_5xx_without_header_backs_off_exponentially():
    codes = iter([503, 500, 200])
    client, clock = make(lambda r: httpx.Response(next(codes), json={"docs": []}))
    client.search({}, 0)
    assert [s for s in clock.slept if s >= 1] == [1.0, 2.0]


def test_404_is_an_error():
    client, _ = make(lambda r: httpx.Response(404, json={}))
    with pytest.raises(BeatSaverError, match="not found"):
        client.maps_by_ids(["abc"])


def test_network_failure_becomes_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client, _ = make(handler)
    with pytest.raises(BeatSaverError, match="unreachable"):
        client.search({}, 0)


def test_rate_limiter_spaces_calls():
    stamps: list[float] = []
    clock = Clock()

    def handler(request: httpx.Request) -> httpx.Response:
        stamps.append(clock.now)
        return httpx.Response(200, json={"docs": []})

    client = BeatSaverClient(httpx.MockTransport(handler), 5.0, clock, clock.sleep)
    for _ in range(6):
        client.search({}, 0)
    gaps = [b - a for a, b in pairwise(stamps)]
    assert all(g >= 0.2 - 1e-9 for g in gaps)
