"""The relight job: start it for a map, and list the environments it can light."""

from saber_tooth.api.core import Api, ApiError
from saber_tooth.service.relight import environment_names


def environments(api: Api) -> dict:
    return {"environments": environment_names(api.service._templates())}


def start_relight(api: Api, raw_id: str, body: object) -> dict:
    """Queue a relight of one map; 422 for an environment the templates cannot light."""
    map_id = api.readable_map(raw_id)
    env = body.get("environment") if isinstance(body, dict) else None
    if not isinstance(env, str) or env not in environment_names(api.service._templates()):
        raise ApiError(422, "environment must be one of GET /api/lightshow/environments")
    args = {"map_id": map_id, "environment": env}
    return {"job": api.jobs.submit("relight", args, map_id=map_id, dedupe=True)}
