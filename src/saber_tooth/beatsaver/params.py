"""Validated parsing of the BeatSaver search query string (shared by the API, presets and MCP)."""

import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Literal, cast

from saber_tooth.beatsaver.filters import DIFFICULTIES, ORDERS, LocalFilter, ServerQuery
from saber_tooth.beatsaver.search import parse_cursor

FILTER_KEYS = frozenset({
    "q", "tags", "min_rating", "min_upvotes",
    "nps_min", "nps_max", "nps_scope", "diffs", "diffs_mode",
    "ranked", "order", "ascending", "from", "to", "bpm_min", "bpm_max", "duration_min",
    "duration_max",
})  # fmt: skip
MAX_Q = 200
MAX_TAGS = 30
MAX_UPVOTES = 1_000_000
DEFAULT_LIMIT = 40
_TAG = re.compile(r"[a-z0-9][a-z0-9 _.+-]{0,39}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_BOOLS = {"": False, "0": False, "false": False, "1": True, "true": True}


@dataclass(frozen=True)
class SearchParams:
    server: ServerQuery
    local: LocalFilter
    cursor: str | None
    limit: int


def _number(raw: str | None, name: str, low: float, high: float) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        value = float(raw) if len(raw) <= 32 and raw.isascii() else math.nan
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be a number from {low:g} to {high:g}")
    return value


def _flag(raw: str | None, name: str) -> bool:
    try:
        return _BOOLS[(raw or "").strip().lower()]
    except KeyError:
        raise ValueError(f"{name} must be true or false") from None


def _day(raw: str | None, name: str) -> str | None:
    if not raw:
        return None
    if not _DATE.fullmatch(raw):
        raise ValueError(f"{name} must be a date YYYY-MM-DD")
    try:
        date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"{name} must be a date YYYY-MM-DD") from None
    return raw


def _csv(raw: str | None) -> list[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def _choice(raw: str | None, name: str, allowed: tuple[str, ...], default: str) -> str:
    value = raw if raw else default
    if value not in allowed:
        raise ValueError(f"{name} must be one of {', '.join(allowed)}")
    return value


def _range(params: dict[str, str], low: str, high: str, top: float) -> tuple[float | None, ...]:
    a, b = (_number(params.get(k), k, 0, top) for k in (low, high))
    if a is not None and b is not None and a > b:
        raise ValueError(f"{low} must not exceed {high}")
    return a, b


def parse_filters(params: dict[str, str]) -> tuple[ServerQuery, LocalFilter]:
    """Server query and local filter from URL-style keys; ValueError names the bad key."""
    q = params.get("q", "").strip()
    if len(q) > MAX_Q:
        raise ValueError(f"q must be at most {MAX_Q} characters")
    tags = tuple(dict.fromkeys(t.lower() for t in _csv(params.get("tags"))))
    if len(tags) > MAX_TAGS or not all(_TAG.fullmatch(t) for t in tags):
        raise ValueError("tags must be a comma list of plain tag names")
    diffs = _csv(params.get("diffs"))
    if not set(diffs) <= set(DIFFICULTIES):
        raise ValueError(f"diffs must be from {', '.join(DIFFICULTIES)}")
    mode = _choice(params.get("diffs_mode"), "diffs_mode", ("all", "any"), "all")
    scope = _choice(params.get("nps_scope"), "nps_scope", ("any", "all"), "any")
    rating = _number(params.get("min_rating"), "min_rating", 0, 1)
    upvotes = _number(params.get("min_upvotes"), "min_upvotes", 0, MAX_UPVOTES)
    if upvotes is not None and not upvotes.is_integer():
        raise ValueError("min_upvotes must be an integer from 0 to 1000000")
    nps_min, nps_max = _range(params, "nps_min", "nps_max", 30)
    bpm_min, bpm_max = _range(params, "bpm_min", "bpm_max", 1000)
    dur_min, dur_max = _range(params, "duration_min", "duration_max", 7200)
    start, end = _day(params.get("from"), "from"), _day(params.get("to"), "to")
    if start and end and start > end:
        raise ValueError("from must not be after to")
    wanted = frozenset(diffs)
    server = ServerQuery(
        q=q,
        tags=tags,
        min_rating=rating,
        min_upvotes=None if upvotes is None else int(upvotes),
        order=_choice(params.get("order"), "order", ORDERS, "Rating"),
        ascending=_flag(params.get("ascending"), "ascending"),
        ranked=_flag(params.get("ranked"), "ranked"),
        date_from=start,
        date_to=end,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        duration_min=None if dur_min is None else int(dur_min),
        duration_max=None if dur_max is None else int(dur_max),
        full_spread=mode == "all" and wanted == set(DIFFICULTIES),
        nps_max=nps_max,
        nps_scope=cast(Literal["any", "all"], scope),
    )
    local = LocalFilter(
        diffs=wanted,
        diffs_mode=cast(Literal["all", "any"], mode),
        nps_min=nps_min,
        nps_max=nps_max,
        nps_scope=cast(Literal["any", "all"], scope),
        min_rating=rating,
        min_upvotes=None if upvotes is None else int(upvotes),
    )
    return server, local


def parse_search(params: dict[str, str], max_limit: int = 100) -> SearchParams:
    """Filters plus `cursor` and `limit`; limit is 1 to max_limit (default 40)."""
    server, local = parse_filters(params)
    raw = params.get("limit", "")
    if raw == "":
        limit = DEFAULT_LIMIT
    elif raw.isascii() and raw.isdigit() and 1 <= int(raw) <= max_limit:
        limit = int(raw)
    else:
        raise ValueError(f"limit must be an integer from 1 to {max_limit}")
    cursor = params.get("cursor") or None
    parse_cursor(cursor)
    return SearchParams(server, local, cursor, limit)
