"""Job handlers per kind, and the job list, view and cancel behind /api/jobs."""

import shutil
from collections.abc import Callable
from pathlib import Path

from saber_tooth.jobs import Handler

UPLOAD_GONE = "the uploaded file is no longer available; upload it again"


def upload_path(data: Path, raw: object) -> Path | None:
    """The stored upload path when it sits in `data/uploads/<box>/`; anything else is refused."""
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        return None
    root = (Path(data) / "uploads").resolve()
    try:
        path = Path(raw).resolve()
    except (OSError, ValueError):
        return None
    return path if path.parent.parent == root else None


def _generate(service, args: dict, progress) -> dict:
    if "url" in args:
        return service.run_generate(args["url"], progress)
    path = upload_path(service.data, args.get("upload"))
    if path is None:
        raise FileNotFoundError(UPLOAD_GONE)
    try:
        if not path.is_file():
            raise FileNotFoundError(UPLOAD_GONE)
        return service.run_generate(str(path), progress)
    finally:
        shutil.rmtree(path.parent, ignore_errors=True)


def core_handlers(service) -> dict[str, Handler]:
    return {
        "scan": lambda a, p: service.run_scan(a["map_id"], p),
        "apply": lambda a, p: service.run_apply(a["map_id"], p),
        "fix": lambda a, p: service.fix_map(a["map_id"], progress=p),
        "learn": lambda a, p: {"units": service.learn(p)},
        "generate": lambda a, p: _generate(service, a, p),
        "crop": lambda a, p: service.crop_map(
            a["map_id"], a["start"], a["end"], a["replace"], progress=p
        ),
    }


KIND_LABELS = {
    "scan": "Scan",
    "fix": "Fix",
    "apply": "Apply",
    "crop": "Crop",
    "learn": "Learn lightshows",
    "bs-download": "Download maps",
}
VIEW_FIELDS = (
    "id",
    "kind",
    "status",
    "map_id",
    "created_at",
    "started_at",
    "updated_at",
    "progress",
    "progress_at",
    "error",
)


def _never(job_id: str) -> bool:
    return False


def _title(row: dict) -> str:
    if row.get("map_title"):
        return row["map_title"]
    if row["kind"] == "generate":
        return "Generate from YouTube" if "url" in row["args"] else "Generate from file"
    return KIND_LABELS.get(row["kind"], row["kind"])


def view(
    row: dict, position: int | None = None, cancelling: Callable[[str], bool] = _never
) -> dict:
    out = {k: row.get(k) for k in VIEW_FIELDS}
    out["cancel_requested"] = row["status"] == "running" and cancelling(row["id"])
    out["title"] = _title(row)
    out["map_exists"] = bool(row.get("map_exists"))
    out["position"] = position
    return out


def list_jobs(store, cancelling: Callable[[str], bool] = _never) -> dict:
    lists = store.job_lists()
    active = {r["map_id"] for k in ("running", "queued") for r in lists[k] if r.get("map_id")}
    # an active job on a map hides that map's finished entry: one entry per song
    lists["recent"] = [r for r in lists["recent"] if r.get("map_id") not in active]
    return {
        "running": [view(r, None, cancelling) for r in lists["running"]],
        "queued": [view(r, n, cancelling) for n, r in enumerate(lists["queued"], start=1)],
        "recent": [view(r, None, cancelling) for r in lists["recent"]],
    }


def job_detail(store, job_id: str, cancelling: Callable[[str], bool] = _never) -> dict:
    """One job with its result; raises KeyError for an unknown id."""
    row = store.job(job_id)
    found = store.get_map(row["map_id"]) if row.get("map_id") else None
    row["map_title"] = found["title"] if found else None
    row["map_exists"] = found is not None
    out = view(row, store.queue_position(job_id), cancelling)
    out["result"] = row["result"]
    return out
