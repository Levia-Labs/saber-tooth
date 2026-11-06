"""HTTP client for the beat-analyser container."""

import logging
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from saber_tooth.analyser_gate import analyser_slot, slots_from_env
from saber_tooth.analysis import Analysis, read_project

log = logging.getLogger(__name__)
_ZIP_SUFFIX = "_tracks.zip"
STAGE_TIMEOUT_S = 900.0  # one analyser request may run this long before it is reported
POLL_S = 0.2  # how often the wait looks at the cancel flag
ATTEMPTS = 3  # tries per analysis before the failure is reported
BACKOFF_S = 2.0  # wait before the second try; doubled before each later one
_FILENAME = re.compile(r'filename="?([^";]+)"?')
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


class AnalyserError(Exception):
    """beat-analyser refused or failed the request; `transient` errors are worth another try."""

    transient = False


class AnalyserTimeout(AnalyserError):
    """beat-analyser did not answer within the stage timeout."""

    transient = True


class AnalyserBusy(AnalyserError):
    """beat-analyser was unreachable or failed server-side."""

    transient = True


class AnalyserClient:
    def __init__(
        self,
        base_url: str,
        uploads: Path,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 1800.0,
        stage_timeout: float = STAGE_TIMEOUT_S,
        attempts: int = ATTEMPTS,
        backoff: float | None = None,
        slots: int | None = None,
        lock_dir: Path | None = None,
    ) -> None:
        self.uploads = uploads
        # Slot locks need a writable folder every worker shares; the uploads mount is read-only.
        self.lock_dir = lock_dir if lock_dir is not None else uploads / ".slots"
        self.attempts, self.backoff = max(1, attempts), backoff
        self.slots = slots if slots is not None else slots_from_env()
        self.stage_timeout = stage_timeout
        self._client = httpx.Client(
            base_url=base_url,
            transport=transport,
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    def analyse_url(self, url: str, cancel: Callable[[], None] | None = None) -> Analysis:
        return self._finish(
            self._run(lambda: self._post("/download_yt", json={"url": url}), cancel)
        )

    def analyse_file(
        self, path: Path, name: str, cancel: Callable[[], None] | None = None
    ) -> Analysis:
        """Analyse one audio file. `cancel` is polled while waiting and raises to stop the wait."""

        def upload() -> httpx.Response:
            with path.open("rb") as handle:
                return self._post("/upload", files={"file": (name, handle)})

        return self._finish(self._run(upload, cancel))

    def _run(self, call: Callable[[], httpx.Response], cancel) -> httpx.Response:
        """One request at a time per slot, retried with backoff while the failure is transient."""
        for attempt in range(1, self.attempts + 1):
            try:
                with analyser_slot(self.lock_dir, self.slots, cancel):
                    return self._send(call, cancel)
            except AnalyserError as exc:
                log.warning("analyser attempt %d of %d failed: %s", attempt, self.attempts, exc)
                if not exc.transient or attempt == self.attempts:
                    raise
            wait = BACKOFF_S if self.backoff is None else self.backoff
            self._pause(wait * 2 ** (attempt - 1), cancel)
        raise AssertionError("unreachable")

    @staticmethod
    def _pause(seconds: float, cancel) -> None:
        end = time.monotonic() + seconds
        while (left := end - time.monotonic()) > 0:
            if cancel is not None:
                cancel()
            time.sleep(min(left, POLL_S))

    def _post(self, route: str, **kwargs) -> httpx.Response:
        limit = httpx.Timeout(self.stage_timeout, connect=10.0)
        try:
            response = self._client.post(route, timeout=limit, **kwargs)
        except httpx.TimeoutException as exc:
            raise AnalyserTimeout(self._slow()) from exc
        except httpx.HTTPError as exc:
            raise AnalyserBusy(f"beat-analyser unreachable: {exc!r}") from exc
        if response.is_error:
            kind = AnalyserBusy if response.status_code >= 500 else AnalyserError
            raise kind(_error_message(response))
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
