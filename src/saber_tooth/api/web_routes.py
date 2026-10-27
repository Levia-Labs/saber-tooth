"""Library, cover and single-page-app routes."""

import os
import re
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse

from saber_tooth.api.core import Api, ApiError, _error
from saber_tooth.api.library import MAPPER_SEP, MAX_COVER_BYTES
from saber_tooth.api.static import SHELL_CACHE

COVER_CACHE = "private, max-age=86400"


def _etag_matches(header: str | None, etag: str) -> bool:
    if not header:
        return False
    wanted = [t.strip().removeprefix("W/") for t in header.split(",")]
    return "*" in wanted or etag in wanted


_RANGE = re.compile(r"(\d*)-(\d*)")


def _range_ok(header: str | None) -> bool:
    """False for a Range header that is malformed or has an inverted or empty spec."""
    if not header:
        return True
    unit, _, specs = header.partition("=")
    if unit.strip().lower() != "bytes":
        return True  # unknown unit: ignored, full body
    for spec in specs.split(","):
        m = _RANGE.fullmatch(spec.strip())
        if m is None or not (m[1] or m[2]) or (m[1] and m[2] and int(m[1]) > int(m[2])):
            return False
    return True


def read_cover(path: Path) -> tuple[bytes, str] | None:
    """Cover bytes and ETag from one open handle, or None when missing or over the cap."""
    try:
        with path.open("rb") as fh:
            st = os.fstat(fh.fileno())
            if st.st_size > MAX_COVER_BYTES:
                return None
            data = fh.read(MAX_COVER_BYTES + 1)
    except OSError:
        return None
    if len(data) > MAX_COVER_BYTES:
        return None
    return data, f'"{st.st_mtime_ns:x}-{st.st_size:x}"'


def register(app: FastAPI, api: Api, web: Path) -> None:
    @app.get("/api/maps")
    def maps(request: Request):
        qp = request.query_params
        params = {k: qp[k] for k in qp}
        for key in ("status", "env"):  # repeatable as well as comma-separated
            if key in qp:
                params[key] = ",".join(qp.getlist(key))
        if "mapper" in qp:  # exact names may contain commas: join on a separator, not a comma
            params["mapper"] = MAPPER_SEP.join(qp.getlist("mapper"))
        if "level" in qp:
            params["level"] = ",".join(qp.getlist("level"))
        return api.maps_page(params)

    @app.get("/api/maps/facets")
    def facets():
        return api.facets()

    @app.get("/api/maps/{map_id}")
    def map_detail(map_id: str):
        return api.map_item(map_id)

    @app.get("/api/maps/{map_id}/cover")
    def cover(map_id: str, request: Request):
        path, ctype = api.cover(map_id)
        loaded = read_cover(path)
        if loaded is None:
            raise ApiError(404, f"no cover for map: {map_id}")
        data, etag = loaded
        headers = {"ETag": etag, "Cache-Control": COVER_CACHE}
        if _etag_matches(request.headers.get("if-none-match"), etag):
            return Response(status_code=304, headers=headers)
        return Response(data, media_type=ctype, headers=headers)

    @app.get("/api/maps/{map_id}/audio")
    def audio(map_id: str, request: Request):
        path, ctype = api.audio(map_id)
        try:
            st = path.stat()
        except OSError:
            raise ApiError(404, f"no audio for map: {map_id}") from None
        etag = f'"{st.st_mtime_ns:x}-{st.st_size:x}"'
        headers = {"ETag": etag, "Cache-Control": COVER_CACHE, "Accept-Ranges": "bytes"}
        if not _range_ok(request.headers.get("range")):
            return Response(
                status_code=416, headers={**headers, "Content-Range": f"bytes */{st.st_size}"}
            )
        if _etag_matches(request.headers.get("if-none-match"), etag):
            return Response(status_code=304, headers=headers)
        return FileResponse(path, media_type=ctype, headers=headers, stat_result=st)

    @app.api_route("/api/{rest:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def unknown_api(rest: str):
        return _error(404, "not found")

    @app.get("/maps/{map_id}", include_in_schema=False)
    @app.get("/new", include_in_schema=False)
    def spa(map_id: str = ""):
        return FileResponse(
            web / "index.html", media_type="text/html", headers={"Cache-Control": SHELL_CACHE}
        )
