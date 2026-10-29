"""Job handlers per kind, and the job list, view and cancel behind /api/jobs."""

import shutil
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


def _generate(service, args: dict) -> dict:
    if "url" in args:
        return service.run_generate(args["url"])
    path = upload_path(service.data, args.get("upload"))
    if path is None:
        raise FileNotFoundError(UPLOAD_GONE)
    try:
        if not path.is_file():
            raise FileNotFoundError(UPLOAD_GONE)
        return service.run_generate(str(path))
    finally:
        shutil.rmtree(path.parent, ignore_errors=True)


def core_handlers(service) -> dict[str, Handler]:
    return {
        "scan": lambda a, p: service.run_scan(a["map_id"]),
        "apply": lambda a, p: service.run_apply(a["map_id"]),
        "fix": lambda a, p: service.fix_map(a["map_id"], progress=p),
        "learn": lambda a, p: {"units": service.learn()},
        "generate": lambda a, p: _generate(service, a),
        "crop": lambda a, p: service.crop_map(a["map_id"], a["start"], a["end"], a["replace"]),
    }
