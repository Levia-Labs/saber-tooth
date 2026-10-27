"""Validated query parsing and local filtering for BeatSaver playlist search."""

from dataclasses import dataclass

from saber_tooth.beatsaver.models import BsPlaylist
from saber_tooth.beatsaver.params import MAX_Q, _day, _flag, _number, _range

PLAYLIST_ORDERS = ("Latest", "Relevance", "Rating", "Curated")
MAX_COUNT = 1_000_000
MAX_SECONDS = 360_000


@dataclass(frozen=True)
class PlaylistFilter:
    """Filters BeatSaver cannot apply to playlists; None means unbounded."""

    maps_min: int | None = None
    maps_max: int | None = None
    min_rating: float | None = None
    min_upvotes: int | None = None
    duration_min: int | None = None
    duration_max: int | None = None

    def matches(self, p: BsPlaylist) -> bool:
        checks = (
            (self.maps_min, p.maps_count, True),
            (self.maps_max, p.maps_count, False),
            (self.min_rating, p.rating, True),
            (self.min_upvotes, p.upvotes, True),
            (self.duration_min, p.duration, True),
            (self.duration_max, p.duration, False),
        )
        return all(
            bound is None or (value >= bound if lower else value <= bound)
            for bound, value, lower in checks
        )


@dataclass(frozen=True)
class PlaylistQuery:
    server: dict[str, str]
    local: PlaylistFilter
    cursor: int


def _whole(value: float | None) -> int | None:
    return None if value is None else int(value)


def parse_playlist_query(params: dict[str, str]) -> PlaylistQuery:
    """ValueError names the bad key. include_empty is never accepted: it is always false."""
    q = params.get("q", "").strip()
    if len(q) > MAX_Q:
        raise ValueError(f"q must be at most {MAX_Q} characters")
    order = params.get("order") or "Latest"
    if order not in PLAYLIST_ORDERS:
        raise ValueError(f"order must be one of {', '.join(PLAYLIST_ORDERS)}")
    start, end = _day(params.get("from"), "from"), _day(params.get("to"), "to")
    if start and end and start > end:
        raise ValueError("from must not be after to")
    nps_min, nps_max = _range(params, "min_nps", "max_nps", 30)
    maps_min, maps_max = _range(params, "maps_min", "maps_max", MAX_COUNT)
    dur_min, dur_max = _range(params, "duration_min", "duration_max", MAX_SECONDS)
    rating = _number(params.get("min_rating"), "min_rating", 0, 1)
    upvotes = _number(params.get("min_upvotes"), "min_upvotes", 0, MAX_COUNT)
    if upvotes is not None and not upvotes.is_integer():
        raise ValueError("min_upvotes must be an integer")
    raw = params.get("cursor") or "0"
    if not (raw.isascii() and raw.isdigit() and len(raw) <= 6):
        raise ValueError("cursor must be a page number")
    server = {"order": order}
    if q:
        server["q"] = q
    if _flag(params.get("ascending"), "ascending"):
        server["ascending"] = "true"
    for key, on in (("curated", _flag(params.get("curated"), "curated")),
                    ("verified", _flag(params.get("verified"), "verified"))):  # fmt: skip
        if on:
            server[key] = "true"
    for key, value in (("minNps", nps_min), ("maxNps", nps_max)):
        if value is not None:
            server[key] = f"{value:g}"
    for key, day in (("from", start), ("to", end)):
        if day:
            server[key] = day
    local = PlaylistFilter(
        _whole(maps_min),
        _whole(maps_max),
        rating,
        _whole(upvotes),
        _whole(dur_min),
        _whole(dur_max),
    )
    return PlaylistQuery(server, local, int(raw))
