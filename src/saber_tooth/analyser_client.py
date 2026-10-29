"""HTTP client for the beat-analyser container."""

import re
import threading
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from saber_tooth.analysis import Analysis, read_project

_ZIP_SUFFIX = "_tracks.zip"
STAGE_TIMEOUT_S = 900.0  # one analyser request may run this long before it is reported
POLL_S = 0.2  # how often the wait looks at the cancel flag
_FILENAME = re.compile(r'filename="?([^";]+)"?')
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


class AnalyserError(Exception):
    """beat-analyser refused or failed the request."""


class AnalyserTimeout(AnalyserError):
    """beat-analyser did not answer within the stage timeout."""


class AnalyserClient:
    def __init__(
        self,
        base_url: str,
        uploads: Path,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 1800.0,
        stage_timeout: float = STAGE_TIMEOUT_S,
    ) -> None:
        self.uploads = uploads
        self.stage_timeout = stage_timeout
        self._client = httpx.Client(
            base_url=base_url,
            transport=transport,
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    def analyse_url(self, url: str, cancel: Callable[[], None] | None = None) -> Analysis:
        return self._finish(
            self._send(lambda: self._post("/download_yt", json={"url": url}), cancel)
        )

    def analyse_file(
        self, path: Path, name: str, cancel: Callable[[], None] | None = None
    ) -> Analysis:
        """Analyse one audio file. `cancel` is polled while waiting and raises to stop the wait."""

        def upload() -> httpx.Response:
            with path.open("rb") as handle:
                return self._post("/upload", files={"file": (name, handle)})

        return self._finish(self._send(upload, cancel))

    def _post(self, route: str, **kwargs) -> httpx.Response:
        limit = httpx.Timeout(self.stage_timeout, connect=10.0)
        try:
            response = self._client.post(route, timeout=limit, **kwargs)
        except httpx.TimeoutException as exc:
            raise AnalyserTimeout(self._slow()) from exc
        except httpx.HTTPError as exc:
            raise AnalyserError(f"beat-analyser unreachable: {exc}") from exc
        if response.is_error:
            raise AnalyserError(_error_message(response))
        return response

    def _send(self, call: Callable[[], httpx.Response], cancel) -> httpx.Response:
        """Run the request in a worker thread so a cancel or the stage timeout ends the wait."""
        box: dict = {}

        def run() -> None:
            try:
                box["response"] = call()
            except BaseException as exc:  # handed to the waiting thread below
                box["error"] = exc

        worker = threading.Thread(target=run, name="analyser-request", daemon=True)
        worker.start()
        deadline = time.monotonic() + self.stage_timeout + 1.0
        while worker.is_alive() and time.monotonic() < deadline:
            if cancel is not None:
                cancel()  # raises when the job was cancelled; the request is abandoned
            worker.join(POLL_S)
        if "error" in box:
            raise box["error"]
        if "response" not in box:
            raise AnalyserTimeout(self._slow())
        return box["response"]

    def _slow(self) -> str:
        return f"beat-analyser did not answer within {self.stage_timeout:g} s"

    def _finish(self, response: httpx.Response) -> Analysis:
        name = _project_name(response.headers.get("content-disposition", ""))
        root = self.uploads.resolve()
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
