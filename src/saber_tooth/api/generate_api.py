"""Submitting a generate job: one import per source, and the song title as soon as it is known."""

import threading
from collections.abc import Callable
from pathlib import Path

from saber_tooth.source import file_source, url_source, video_title


class Conflict(Exception):
    """The source is already imported or being imported; `fields` go into the answer."""

    def __init__(self, message: str, fields: dict) -> None:
        super().__init__(message)
        self.fields = fields


def source_of(args: dict) -> str | None:
    """The source key of a stored generate job: its own, else derived from its link."""
    if isinstance(args.get("source"), str):
        return args["source"]
    return url_source(args["url"]) if isinstance(args.get("url"), str) else None


class GenerateSubmitter:
    def __init__(self, api, lookup: Callable[[str], str | None] | None = None) -> None:
        self.api = api
        self.lookup = lookup  # None: the oEmbed lookup
        self._lock = threading.Lock()
        self._backfilled = False

    def _check(self, source: str) -> None:
        store = self.api.store
        if not self._backfilled:
            store.backfill_sources(source_of)
            self._backfilled = True
        job = store.active_source_job(source)
        if job:
            raise Conflict("already being imported", {"job": job})
        found = store.find_source(source)
        if found:
            raise Conflict("already imported", {"map_id": found["id"]})

    def _submit(self, source: str, args: dict) -> str:
        with self._lock:
            self._check(source)
            return self.api.jobs.submit("generate", {**args, "source": source})

    def url(self, url: str) -> str:
        source = url_source(url)
        self._check(source)  # refuse before the slow title lookup
        title = (self.lookup or video_title)(url)
        return self._submit(source, {"url": url, **({"title": title} if title else {})})

    def file(self, path: Path) -> str:
        return self._submit(file_source(path), {"upload": str(path)})
