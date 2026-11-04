"""Restarting a failed or cancelled job: a copy with the same kind, map and stored arguments."""

from saber_tooth.api.jobs_api import upload_path

MAP_JOBS = ("scan", "fix", "apply", "crop", "relight", "regenerate")  # kinds that need a map


def retry_job(api, raw: str) -> dict:
    """Queue a copy of a failed or cancelled job; `api` is the `Api` the job belongs to."""
    from saber_tooth.api.core import ApiError  # core imports this module

    try:
        old = api.store.job(api._job_id(raw))
    except KeyError:
        raise ApiError(404, f"unknown job: {raw}") from None
    if old["status"] not in ("failed", "cancelled"):
        raise ApiError(409, "only a failed or cancelled job can be restarted")
    if old["kind"] in MAP_JOBS and not old["map_id"]:
        raise ApiError(409, "this job's map is gone")
    if old["kind"] == "generate" and "upload" in old["args"]:  # the only temp input
        path = upload_path(api.service.data, old["args"]["upload"])
        if path is None or not path.is_file():
            raise ApiError(409, "the uploaded audio is gone; upload it again")
    return api.job(api.jobs.submit(old["kind"], old["args"], old["map_id"]))
