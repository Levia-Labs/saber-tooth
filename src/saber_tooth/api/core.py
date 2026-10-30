"""API route logic over one Service."""

import logging
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from fastapi.responses import JSONResponse

from saber_tooth.api.jobs_api import core_handlers, job_detail, list_jobs, upload_path
from saber_tooth.api.library import (
    AUDIO_TYPES,
    COVER_TYPES,
    MAX_LIMIT,
    Extras,
    audio_path,
    cover_path,
    folder_path,
    parse_query,
    shape_item,
)
from saber_tooth.api.proposal_views import map_findings, proposal_views
from saber_tooth.jobs import Jobs
from saber_tooth.service import MapNotFound, MapUnreadable, Service
from saber_tooth.store import ProposalApplied

log = logging.getLogger(__name__)


MAP_ID = re.compile(r"[0-9a-f]{12}")
JOB_ID = re.compile(r"[0-9a-f]{32}")

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
        for kind, handler in core_handlers(service).items():
            self.jobs.register(kind, handler)
        self.extras = Extras()

    # ids ---------------------------------------------------------------------

    def map_id(self, raw: str) -> str:
        if not MAP_ID.fullmatch(raw) or not any(m["id"] == raw for m in self.store.list_maps()):
            raise MapNotFound(f"unknown map: {raw}")
        return raw

    @staticmethod
    def proposal_id(raw: str) -> int:
        if not raw.isascii() or not raw.isdigit() or len(raw) > 15:
            raise ApiError(404, f"unknown proposal: {raw}")
        return int(raw)

    # maps and proposals --------------------------------------------------------

    def maps_page(self, params: dict[str, str], max_limit: int = MAX_LIMIT) -> dict:
        try:
            query = parse_query(params, max_limit)
        except ValueError as exc:
            raise ApiError(400, str(exc)) from None
        self.service.refresh_if_changed()
        rows, total = self.store.query_maps(
            query.offset,
            query.limit,
            query.sort,
            query.order,
            query.q,
            query.status,
            query.env,
            query.q_fields,
            query.mapper,
            query.level,
            query.level_mode,
            query.duration_min,
            query.duration_max,
            query.bpm_min,
            query.bpm_max,
        )
        items = [shape_item(r, self.service.levels, self.extras) for r in rows]
        return {"items": items, "total": total, "offset": query.offset, "limit": query.limit}

    def facets(self) -> dict:
        self.service.refresh_if_changed()
        return self.store.facets()

    def map_item(self, raw: str) -> dict:
        self.service.refresh_if_changed()
        row = self.store.get_map(self.map_id(raw))
        if row is None:
            raise MapNotFound(f"unknown map: {raw}")
        return shape_item(row, self.service.levels, self.extras)

    def cover(self, raw: str) -> tuple[Path, str]:
        """Path and content type of a map's cover image; MapNotFound when there is none."""
        row = self.store.get_map(self.map_id(raw))
        folder = folder_path(self.service.levels, row["folder"]) if row else None
        if row is None or folder is None or row["parse_error"]:
            raise MapNotFound(f"no cover for map: {raw}")
        path = cover_path(folder, self.extras.get(folder).cover)
        if path is None:
            raise MapNotFound(f"no cover for map: {raw}")
        return path, COVER_TYPES[path.suffix.lower()]

    def audio(self, raw: str) -> tuple[Path, str]:
        """Path and content type of a map's song; MapNotFound when there is none."""
        row = self.store.get_map(self.map_id(raw))
        folder = folder_path(self.service.levels, row["folder"]) if row else None
        if row is None or folder is None or row["parse_error"]:
            raise MapNotFound(f"no audio for map: {raw}")
        path = audio_path(folder, self.extras.get(folder).song)
        if path is None:
            raise MapNotFound(f"no audio for map: {raw}")
        return path, AUDIO_TYPES[path.suffix.lower()]

    def proposals(self, map_id: str) -> list[dict]:
        return proposal_views(self, map_id)

    def findings(self, map_id: str) -> dict:
        return map_findings(self, map_id)

    def set_status(self, raw: str, status: str) -> dict:
        pid = self.proposal_id(raw)
        current = self.store.proposal(pid)
        if current is None:
            raise ApiError(404, f"unknown proposal: {pid}")
        if current["status"] in ("applied", "superseded"):
            raise ApiError(409, f"proposal already {current['status']}")
        try:
            self.store.set_status(pid, status)
        except KeyError:
            raise ApiError(404, f"unknown proposal: {pid}") from None
        except ProposalApplied:
            raise ApiError(409, "proposal already applied") from None
        return {"id": pid, "status": status}

    def approve_all(self, map_id: str) -> dict:
        pending = [p for p in self.store.proposals(self.map_id(map_id))]
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

    def readable_map(self, raw: str) -> str:
        """The map id: 404 when unknown, `MapUnreadable` when its parse failed."""
        map_id = self.map_id(raw)
        row = next(m for m in self.store.list_maps() if m["id"] == map_id)
        if row["parse_error"]:
            raise MapUnreadable(f"map {row['folder']} cannot be read: {row['parse_error']}")
        return map_id

    def scan(self, map_id: str) -> dict:
        map_id = self.readable_map(map_id)
        return {"job": self.jobs.submit("scan", {"map_id": map_id}, map_id=map_id, dedupe=True)}

    def apply(self, map_id: str) -> dict:
        self.map_id(map_id)
        return {"job": self.jobs.submit("apply", {"map_id": map_id}, map_id=map_id, dedupe=True)}

    def fix(self, map_id: str) -> dict:
        map_id = self.readable_map(map_id)
        return {"job": self.jobs.submit("fix", {"map_id": map_id}, map_id=map_id, dedupe=True)}

    def lightshow(self) -> dict:
        return self.service.lightshow_info()

    def learn(self) -> dict:
        return {"job": self.jobs.submit("learn")}

    def generate_url(self, url: object) -> dict:
        if not _is_youtube_url(url):
            raise ApiError(400, "only YouTube URLs are supported")
        return {"job": self.jobs.submit("generate", {"url": url})}

    def generate_file(self, path: Path) -> dict:
        try:
            return {"job": self.jobs.submit("generate", {"upload": str(path)})}
        except BaseException:
            shutil.rmtree(path.parent, ignore_errors=True)
            raise

    def _job_id(self, raw: str) -> str:
        if not JOB_ID.fullmatch(raw):
            raise ApiError(404, f"unknown job: {raw}")
        return raw

    def job(self, raw: str) -> dict:
        try:
            return job_detail(self.store, self._job_id(raw), self.jobs.cancel_requested)
        except KeyError:
            raise ApiError(404, f"unknown job: {raw}") from None

    def jobs_list(self) -> dict:
        return list_jobs(self.store, self.jobs.cancel_requested)

    def retry_job(self, raw: str) -> dict:
        """Queue a copy of a failed or cancelled job (same kind, map and stored args)."""
        try:
            old = self.store.job(self._job_id(raw))
        except KeyError:
            raise ApiError(404, f"unknown job: {raw}") from None
        if old["status"] not in ("failed", "cancelled"):
            raise ApiError(409, "only a failed or cancelled job can be restarted")
        if old["kind"] in ("scan", "fix", "apply", "crop", "relight") and not old["map_id"]:
            raise ApiError(409, "this job's map is gone")
        if old["kind"] == "generate" and "upload" in old["args"]:  # the only temp input
            path = upload_path(self.service.data, old["args"]["upload"])
            if path is None or not path.is_file():
                raise ApiError(409, "the uploaded audio is gone; upload it again")
        new_id = self.jobs.submit(old["kind"], old["args"], old["map_id"])
        return self.job(new_id)

    def cancel_job(self, raw: str) -> dict:
        try:
            outcome = self.store.cancel_job(self._job_id(raw))
        except KeyError:
            raise ApiError(404, f"unknown job: {raw}") from None
        if outcome == "running":
            self.jobs.request_cancel(self._job_id(raw))
        elif outcome != "cancelled":
            raise ApiError(409, "the job already finished")
        view = self.job(raw)
        # The job can stop between reading its row and its cancel flag (the flag is cleared once
        # it ends), so a row still read as running answers with the request it just received.
        if outcome == "running" and view["status"] == "running":
            view["cancel_requested"] = True
        return view
