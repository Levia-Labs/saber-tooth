"""Regenerate and bulk fix routes, and the library-wide findings summary."""

from fastapi import FastAPI

from saber_tooth.api.core import Api, ApiError
from saber_tooth.findings_summary import findings_summary, maps_with_findings
from saber_tooth.generated import generated_ids, is_generated


def _queue(api: Api, kind: str, ids: list[str]) -> dict:
    jobs = [api.jobs.submit(kind, {"map_id": i}, map_id=i, dedupe=True) for i in ids]
    return {"count": len(jobs), "jobs": jobs}


def regenerate_one(api: Api, raw: str) -> dict:
    map_id = api.readable_map(raw)
    if not is_generated(api.store, api.service.levels, map_id):
        raise ApiError(409, "only generated maps can be regenerated")
    job = api.jobs.submit("regenerate", {"map_id": map_id}, map_id=map_id, dedupe=True)
    return {"job": job}


def regenerate_all(api: Api) -> dict:
    return _queue(api, "regenerate", generated_ids(api.store, api.service.levels))


def fix_all(api: Api) -> dict:
    return _queue(api, "fix", maps_with_findings(api.store))


def register(app: FastAPI, api: Api) -> None:
    @app.post("/api/maps/regenerate-all")
    def _regenerate_all():
        return regenerate_all(api)

    @app.post("/api/maps/fix-all")
    def _fix_all():
        return fix_all(api)

    @app.post("/api/maps/{map_id}/regenerate")
    def _regenerate(map_id: str):
        return regenerate_one(api, map_id)

    @app.get("/api/findings/summary")
    def _summary():
        return findings_summary(api.store, api.service.levels)
