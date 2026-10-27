"""Cursor search: BeatSaver pages narrowed by the server query, then by the local filter."""

import hashlib
import json
import re
from dataclasses import dataclass, field

from saber_tooth.beatsaver.cache import BsCache
from saber_tooth.beatsaver.client import BeatSaverClient, BeatSaverError
from saber_tooth.beatsaver.filters import LocalFilter, ServerQuery
from saber_tooth.beatsaver.models import BsMap

_CURSOR = re.compile(r"([0-9]{1,6})\.([0-9]{1,6})")
MAX_LIMIT = 100


@dataclass
class SearchResult:
    items: list[BsMap] = field(default_factory=list)
    cursor: str | None = None
    scanned: int = 0
    matched: int = 0
    partial_reason: str | None = None
    retry_after: float | None = None


def parse_cursor(cursor: str | None) -> tuple[int, int]:
    """(page, offset) of the next unseen BeatSaver map; ValueError when malformed."""
    if cursor is None:
        return 0, 0
    found = _CURSOR.fullmatch(cursor)
    if not found:
        raise ValueError("invalid cursor")
    return int(found.group(1)), int(found.group(2))


def query_key(params: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def _page_maps(
    client: BeatSaverClient, cache: BsCache, params: dict[str, str], key: str, page: int
) -> list[BsMap]:
    ids = cache.get_query(key, page)
    if ids is not None:
        cached = cache.get_maps(ids)
        if len(cached) == len(ids):
            return [cached[i] for i in ids]
    maps = client.search(params, page)
    cache.put_maps(maps)
    cache.put_query(key, page, [m.id for m in maps])
    return maps


def search(
    client: BeatSaverClient,
    cache: BsCache,
    server: ServerQuery,
    local: LocalFilter,
    cursor: str | None,
    limit: int = 40,
    max_pages: int = 10,
    scope: str = "",
) -> SearchResult:
    """Collect up to `limit` matches, scanning at most `max_pages` BeatSaver pages.

    The cursor names the next unseen map, so a scan that finds nothing still advances it. A
    BeatSaver failure after some progress returns what was found, with the reason and retry hint.
    """
    page, offset = parse_cursor(cursor)
    limit = max(1, min(limit, MAX_LIMIT))
    params = server.to_params()
    key = query_key({**params, "_scope": scope})
    res = SearchResult(cursor=cursor)
    fetched = 0
    while len(res.items) < limit and fetched < max_pages:
        try:
            docs = _page_maps(client, cache, params, key, page)
        except BeatSaverError as exc:
            if not res.scanned and not res.items:
                raise
            res.partial_reason, res.retry_after = str(exc), exc.retry_after
            res.cursor = f"{page}.{offset}"
            res.matched = len(res.items)
            return res
        fetched += 1
        if not docs:
            res.cursor, res.matched = None, len(res.items)
            return res
        for i in range(offset, len(docs)):
            res.scanned += 1
            if local.matches(docs[i]):
                res.items.append(docs[i])
                if len(res.items) >= limit:
                    offset = i + 1
                    break
        else:
            offset = len(docs)
        if offset >= len(docs):
            page, offset = page + 1, 0
        res.cursor = f"{page}.{offset}"
    res.matched = len(res.items)
    return res
