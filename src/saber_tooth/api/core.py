"""API route logic over one Service."""

import logging
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from fastapi.responses import JSONResponse

from saber_tooth.fixer.codec import note_to_dict
from saber_tooth.jobs import Jobs
from saber_tooth.mapio import MapParseError, load_map
from saber_tooth.service import MapNotFound, MapUnreadable, Service
from saber_tooth.service.core import CREATE_MAP, STAGING_PREFIX
from saber_tooth.store import ProposalApplied

log = logging.getLogger(__name__)


MAP_ID = re.compile(r"[0-9a-f]{12}")
STAGING_ID = re.compile(re.escape(STAGING_PREFIX) + r"[0-9a-f]{32}")
JOB_ID = re.compile(r"[0-9a-f]{32}")
PROPOSAL_FIELDS = ("id", "rule", "difficulty", "severity", "summary", "status", "before", "after")


YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


def _is_youtube_url(url: object) -> bool:
    """True for http(s) URLs on an exact YouTube host, without userinfo or odd characters."""
    if not isinstance(url, str) or not url.isprintable() or "\\" in url or " " in url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        parsed.port  # noqa: B018 - raises ValueError on a malformed port
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        return False
    return host in YOUTUBE_HOSTS


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class Api:
    """Route implementations over one Service."""

    def __init__(self, service: Service) -> None:
        self.service = service
        self.store = service.store
        self.jobs = Jobs(service.store)

    # ids ---------------------------------------------------------------------

    def map_id(self, raw: str, staging: bool = False) -> str:
        if MAP_ID.fullmatch(raw):
            if not any(m["id"] == raw for m in self.store.list_maps()):
                raise MapNotFound(f"unknown map: {raw}")
        elif staging and STAGING_ID.fullmatch(raw):
            if not self.store.proposals(raw):
                raise MapNotFound(f"unknown map: {raw}")
        else:
            raise MapNotFound(f"unknown map: {raw}")
        return raw

    @staticmethod
    def proposal_id(raw: str) -> int:
        if not raw.isascii() or not raw.isdigit() or len(raw) > 15:
            raise ApiError(404, f"unknown proposal: {raw}")
        return int(raw)

    # maps and proposals --------------------------------------------------------

    def maps(self) -> list[dict]:
        self.service.refresh_if_changed()
        rows = []
        for m in self.store.list_maps():
            info = self.store.scan_info(m["id"])
            found = info["findings"] if info else []
            rows.append(
                {
                    **{k: m[k] for k in ("id", "folder", "title", "mapper", "environment")},
                    "parse_error": m["parse_error"],
                    "errors": sum(f["severity"] == "error" for f in found),
                    "warnings": sum(f["severity"] != "error" for f in found),
                }
            )
        return rows

    def _staged_notes(self, proposal: dict) -> list[dict]:
        root = (self.service.data / "staging").resolve()
        try:
            staging = Path(proposal["after"]["staging"]).resolve()
            if staging.parent != root:
                return []
            notes = load_map(staging).difficulties["Expert"].notes
        except (KeyError, TypeError, OSError, MapParseError):
            return []
        return [note_to_dict(n) for n in notes]

    def _view(self, proposal: dict) -> dict:
        view = {k: proposal[k] for k in PROPOSAL_FIELDS}
        if proposal["rule"] == CREATE_MAP:  # the UI shows the Expert notes, not a path
            view.update(difficulty="Expert", before=[], after=self._staged_notes(proposal))
        return view

    def proposals(self, map_id: str) -> list[dict]:
        return [self._view(p) for p in self.store.proposals(self.map_id(map_id, True))]

    def set_status(self, raw: str, status: str) -> dict:
        pid = self.proposal_id(raw)
        current = self.store.proposal(pid)
        if current is None:
            raise ApiError(404, f"unknown proposal: {pid}")
        if current["status"] == "applied":
            raise ApiError(409, "proposal already applied")
        try:
            self.store.set_status(pid, status)
        except KeyError:
            raise ApiError(404, f"unknown proposal: {pid}") from None
        except ProposalApplied:
            raise ApiError(409, "proposal already applied") from None
        return {"id": pid, "status": status}

    def approve_all(self, map_id: str) -> dict:
        pending = [p for p in self.store.proposals(self.map_id(map_id, True))]
        pending = [p for p in pending if p["status"] == "pending"]
        done = 0
        for p in pending:
            try:
                self.store.set_status(p["id"], "approved")
            except (KeyError, ProposalApplied):
                continue
            done += 1
        return {"approved": done}

    # jobs ----------------------------------------------------------------------

    def scan(self, map_id: str) -> dict:
        row = next(m for m in self.store.list_maps() if m["id"] == self.map_id(map_id))
        if row["parse_error"]:
            raise MapUnreadable(f"map {row['folder']} cannot be read: {row['parse_error']}")
        return {"job": self.jobs.submit("scan", self.service.run_scan, map_id)}

    def apply(self, map_id: str) -> dict:
        self.map_id(map_id, True)
        return {"job": self.jobs.submit("apply", self.service.run_apply, map_id)}

    def learn(self) -> dict:
        return {"job": self.jobs.submit("learn", lambda: {"units": self.service.learn()})}

    def generate_url(self, url: object) -> dict:
        if not _is_youtube_url(url):
            raise ApiError(400, "only YouTube URLs are supported")
        return {"job": self.jobs.submit("generate", self.service.run_generate, url)}

    def generate_file(self, path: Path) -> dict:
        def clean() -> None:
            shutil.rmtree(path.parent, ignore_errors=True)

        def run() -> dict:
            try:
                return self.service.run_generate(str(path))
            finally:
                clean()

        try:
            return {"job": self.jobs.submit("generate", run)}
        except BaseException:
            clean()
            raise

    def job(self, raw: str) -> dict:
        try:
            if not JOB_ID.fullmatch(raw):
                raise KeyError(raw)
            j = self.store.job(raw)
        except KeyError:
            raise ApiError(404, f"unknown job: {raw}") from None
        return {k: j[k] for k in ("id", "kind", "status", "error", "result")}
