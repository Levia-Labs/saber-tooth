"""Previous and next map of one map in a filtered, sorted library list."""

from saber_tooth.api.core import Api, ApiError
from saber_tooth.api.library import parse_query

PAGE = 500


def _ref(row: dict) -> dict:
    return {"id": row["id"], "title": row["title"], "folder": row["folder"]}


def neighbors(api: Api, raw: str, params: dict[str, str]) -> dict:
    """Position, total and wrapping neighbours of `raw` in the list `GET /api/maps` would give.

    The list comes from `Store.query_maps`, so filters, search and ordering match the library;
    `offset` and `limit` are ignored. A map outside the list is a 404.
    """
    try:
        q = parse_query({**params, "offset": "0", "limit": "1"})
    except ValueError as exc:
        raise ApiError(400, str(exc)) from None
    map_id = api.map_id(raw)
    api.service.refresh_if_changed()
    rows: list[dict] = []
    total = 1
    while len(rows) < total:
        page, total = api.store.query_maps(
            len(rows), PAGE, q.sort, q.order, q.q, q.status, q.env, q.q_fields, q.mapper,
            q.level, q.level_mode, q.duration_min, q.duration_max, q.bpm_min, q.bpm_max,
        )  # fmt: skip
        if not page:
            break
        rows += page
    index = next((i for i, r in enumerate(rows) if r["id"] == map_id), None)
    if index is None:
        raise ApiError(404, f"map {raw} is not in the filtered list")
    return {
        "index": index + 1,
        "total": len(rows),
        "prev": _ref(rows[index - 1]),
        "next": _ref(rows[(index + 1) % len(rows)]),
    }
