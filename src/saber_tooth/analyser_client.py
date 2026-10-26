"""HTTP client for the beat-analyser container."""

import re
from pathlib import Path

import httpx

from saber_tooth.analysis import Analysis, read_project

_ZIP_SUFFIX = "_tracks.zip"
_FILENAME = re.compile(r'filename="?([^";]+)"?')
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


class AnalyserError(Exception):
    """beat-analyser refused or failed the request."""


class AnalyserClient:
    def __init__(
        self,
        base_url: str,
        uploads: Path,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 1800.0,
    ) -> None:
        self._uploads = uploads
        self._client = httpx.Client(
            base_url=base_url,
            transport=transport,
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    def analyse_url(self, url: str) -> Analysis:
        return self._finish(self._post("/download_yt", json={"url": url}))

    def analyse_file(self, path: Path, name: str) -> Analysis:
        with path.open("rb") as handle:
            response = self._post("/upload", files={"file": (name, handle)})
        return self._finish(response)

    def _post(self, route: str, **kwargs) -> httpx.Response:
        try:
            response = self._client.post(route, **kwargs)
        except httpx.HTTPError as exc:
            raise AnalyserError(f"beat-analyser unreachable: {exc}") from exc
        if response.is_error:
            raise AnalyserError(_error_message(response))
        return response

    def _finish(self, response: httpx.Response) -> Analysis:
        name = _project_name(response.headers.get("content-disposition", ""))
        root = self._uploads.resolve()
        folder = (root / name).resolve()
        if folder.parent != root:
            raise AnalyserError(f"project name escapes uploads: {name!r}")
        return read_project(folder)


def _error_message(response: httpx.Response) -> str:
    try:
        message = response.json().get("error")
    except (ValueError, AttributeError):
        message = None
    return str(message) if message else f"beat-analyser returned HTTP {response.status_code}"


def _project_name(disposition: str) -> str:
    match = _FILENAME.search(disposition)
    if not match or not match.group(1).endswith(_ZIP_SUFFIX):
        raise AnalyserError("response has no project name in Content-Disposition")
    name = match.group(1)[: -len(_ZIP_SUFFIX)]
    if not _NAME.fullmatch(name) or name in {".", ".."}:
        raise AnalyserError(f"invalid project name: {name!r}")
    return name
