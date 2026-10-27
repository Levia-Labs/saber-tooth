"""Rate-limited, host-restricted client for api.beatsaver.com and its download hosts."""

import re
import threading
import time
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from saber_tooth.beatsaver.models import BsMap, BsPlaylist

API = "https://api.beatsaver.com"
HOST_SUFFIX = ".beatsaver.com"
MAX_RETRIES = 4
RETRY_CAP = 60.0
MAX_REDIRECTS = 3
BATCH = 50
SEARCH_KEYS = frozenset({
    "q", "order", "ascending", "tags", "minRating", "maxRating", "minNps", "maxNps", "minBpm",
    "maxBpm", "minDuration", "maxDuration", "fullSpread", "leaderboard", "characteristics",
    "environments", "from", "to", "curated", "verified", "automapper", "chroma", "noodle",
    "cinema", "vivify", "pageSize",
})  # fmt: skip
PLAYLIST_KEYS = frozenset({
    "q", "order", "minNps", "maxNps", "curated", "verified", "includeEmpty", "from", "to",
    "ascending",
})  # fmt: skip
_ID = re.compile(r"[0-9a-fA-F]{1,12}")


class BeatSaverError(Exception):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _version() -> str:
    try:
        return metadata.version("saber-tooth")
    except metadata.PackageNotFoundError:
        return "0"


def download_url_ok(url: object) -> bool:
    """True for an https URL on a *.beatsaver.com host without userinfo or odd characters."""
    if not isinstance(url, str) or not url.isprintable() or "\\" in url or " " in url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password or port not in (None, 443):
        return False
    return host.endswith(HOST_SUFFIX) and len(host) > len(HOST_SUFFIX)


def _retry_after(response: httpx.Response, attempt: int) -> float:
    raw = response.headers.get("retry-after", "")
    try:
        wait = float(raw)
    except ValueError:
        wait = float(2**attempt)
    return min(max(wait, 0.0), RETRY_CAP)


class BeatSaverClient:
    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        rate: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        agent = f"saber-tooth/{_version()} (+https://github.com/Levia-Labs/saber-tooth)"
        self._http = httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": agent},
        )
        self._gap = 1.0 / rate
        self._clock, self._sleep = clock, sleep
        self._next = 0.0
        self._lock = threading.Lock()

    def _pace(self) -> None:
        with self._lock:
            now = self._clock()
            wait = self._next - now
            if wait > 0:
                self._sleep(wait)
                now = max(self._clock(), self._next)
            self._next = now + self._gap

    def _send(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
        """GET with pacing and backoff; the caller closes the returned stream."""
        for attempt in range(MAX_RETRIES + 1):
            self._pace()
            try:
                request = self._http.build_request("GET", url, params=params)
                response = self._http.send(request, stream=True)
            except httpx.HTTPError as exc:
                raise BeatSaverError(f"BeatSaver unreachable: {type(exc).__name__}") from None
            if response.status_code != 429 and response.status_code < 500:
                return response
            wait = _retry_after(response, attempt)
            status = response.status_code
            response.close()
            if attempt == MAX_RETRIES:
                text = "BeatSaver rate limited" if status == 429 else f"BeatSaver error {status}"
                raise BeatSaverError(text, retry_after=wait)
            self._sleep(wait)
        raise AssertionError("unreachable")  # pragma: no cover

    def _json(self, path: str, params: dict[str, str] | None = None) -> dict:
        response = self._send(API + path, params)
        try:
            response.read()
            if response.status_code == 404:
                raise BeatSaverError("not found on BeatSaver")
            if response.status_code >= 400:
                raise BeatSaverError(f"BeatSaver error {response.status_code}")
            data = response.json()
        except (httpx.HTTPError, ValueError):
            raise BeatSaverError("BeatSaver returned an unreadable response") from None
        finally:
            response.close()
        if not isinstance(data, dict):
            raise BeatSaverError("BeatSaver returned an unexpected response")
        return data

    @staticmethod
    def _clean(params: dict[str, str], allowed: frozenset[str]) -> dict[str, str]:
        return {k: str(v) for k, v in params.items() if k in allowed}

    @staticmethod
    def _page(page: int) -> int:
        if not isinstance(page, int) or isinstance(page, bool) or not 0 <= page <= 100_000:
            raise ValueError("page out of range")
        return page

    @staticmethod
    def _maps(items: object) -> list[BsMap]:
        rows = items if isinstance(items, list) else []
        return [BsMap.from_json(x) for x in rows if isinstance(x, dict)]

    def search(self, params: dict[str, str], page: int) -> list[BsMap]:
        data = self._json(f"/search/text/{self._page(page)}", self._clean(params, SEARCH_KEYS))
        return self._maps(data.get("docs"))

    def maps_by_ids(self, ids: list[str]) -> list[BsMap]:
        for i in ids:
            if not _ID.fullmatch(i):
                raise ValueError(f"invalid BeatSaver id: {i!r}")
        found: list[BsMap] = []
        for start in range(0, len(ids), BATCH):
            data = self._json("/maps/ids/" + ",".join(ids[start : start + BATCH]))
            found.extend(BsMap.from_json(v) for v in data.values() if isinstance(v, dict))
        return found

    def playlist_search(self, params: dict[str, str], page: int) -> list[BsPlaylist]:
        path = f"/playlists/search/{self._page(page)}"
        docs = self._json(path, self._clean(params, PLAYLIST_KEYS)).get("docs")
        return [BsPlaylist.from_json(x) for x in docs or [] if isinstance(x, dict)]

    def playlist_page(self, pid: int, page: int) -> list[BsMap]:
        if not isinstance(pid, int) or isinstance(pid, bool) or pid < 0:
            raise ValueError("invalid playlist id")
        rows = self._json(f"/playlists/id/{pid}/{self._page(page)}").get("maps")
        return self._maps([r.get("map") for r in rows or [] if isinstance(r, dict)])

    def download(self, url: str, dest: Path, max_bytes: int) -> Path:
        """Stream a zip from a BeatSaver host into dest; abort and delete it past max_bytes."""
        for _ in range(MAX_REDIRECTS + 1):
            if not download_url_ok(url):
                raise BeatSaverError("refusing download from a non-BeatSaver host")
            response = self._send(url)
            location = response.headers.get("location")
            if response.status_code in (301, 302, 303, 307, 308) and location:
                url = urljoin(url, location)
                response.close()
                continue
            return self._save(response, dest, max_bytes)
        raise BeatSaverError("too many redirects")

    @staticmethod
    def _save(response: httpx.Response, dest: Path, max_bytes: int) -> Path:
        try:
            if response.status_code != 200:
                raise BeatSaverError(f"download failed: HTTP {response.status_code}")
            declared = response.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > max_bytes:
                raise BeatSaverError("download too large")
            total = 0
            try:
                with dest.open("wb") as out:
                    for chunk in response.iter_bytes(65536):
                        total += len(chunk)
                        if total > max_bytes:
                            raise BeatSaverError("download too large")
                        out.write(chunk)
            except httpx.HTTPError:
                dest.unlink(missing_ok=True)
                raise BeatSaverError("download interrupted") from None
            except BeatSaverError:
                dest.unlink(missing_ok=True)
                raise
            return dest
        finally:
            response.close()
