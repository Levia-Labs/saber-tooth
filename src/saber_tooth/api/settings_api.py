"""Service settings, resource figures and the PlaylistManager mod, behind /api/system,
/api/settings and /api/mods/playlistmanager."""

import os
from functools import partial
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool

from saber_tooth.api.core import Api, ApiError
from saber_tooth.jobs_service import PROCESS_KINDS, build_child_handlers
from saber_tooth.mods.beatmods import BeatMods
from saber_tooth.mods.game import game_running
from saber_tooth.mods.playlistmanager import PlaylistManagerMod
from saber_tooth.resources import MAX_WORKERS, snapshot
from saber_tooth.settings import SettingError, Settings

SETTING_KEYS = ("max_concurrent_jobs", "game_dir")


def new_beatmods() -> BeatMods:
    return BeatMods()


class SettingsApi:
    def __init__(self, api: Api, data: Path, levels: Path) -> None:
        self.api = api
        self.settings = Settings(Path(data) / "settings.db")
        self.mod = PlaylistManagerMod(
            self.settings,
            levels,
            lambda: new_beatmods(),
            env=os.environ.get("GAME_DIR") or None,
            running=lambda: game_running(),
        )
        # the pool reads the cap on every pass, so a saved change applies to the next job
        api.jobs.set_limit(lambda: min(self.settings.max_concurrent_jobs(), MAX_WORKERS))

    def system(self) -> dict:
        return {
            **snapshot(),
            "workers": {
                "configured": self.settings.max_concurrent_jobs(),
                "running": self.api.jobs.running_count(),
            },
        }

    def current(self) -> dict:
        game = self.settings.game_dir()
        return {
            "max_concurrent_jobs": self.settings.max_concurrent_jobs(),
            "recommended_max": snapshot()["recommended_max"],
            "game_dir": None if game is None else str(game),
        }

    def update(self, body: object) -> dict:
        if not isinstance(body, dict) or not body or set(body) - set(SETTING_KEYS):
            raise ApiError(400, f"send a JSON object with any of: {', '.join(SETTING_KEYS)}")
        try:
            if "max_concurrent_jobs" in body:
                recommended = snapshot()["recommended_max"]
                self.settings.set_max_concurrent_jobs(body["max_concurrent_jobs"], recommended)
                self.api.jobs.poke()
            if "game_dir" in body:
                self.settings.set_game_dir(body["game_dir"])
        except SettingError as exc:
            raise ApiError(400, str(exc)) from None
        return self.current()

    def install_mod(self, body: object) -> dict:
        if not isinstance(body, dict) or body.get("confirm") is not True:
            raise ApiError(400, 'send {"confirm": true} to install')
        try:
            return self.mod.install()
        except PermissionError as exc:
            raise ApiError(409, str(exc)) from None


def install(app: FastAPI, api: Api, service) -> SettingsApi:
    """Wire settings, the worker cap, worker processes and the routes into the app."""
    sa = SettingsApi(api, service.data, service.levels)
    spec = getattr(service, "child_spec", None)
    if spec is not None:  # only the production service can be rebuilt inside a worker process
        api.jobs.enable_processes(partial(build_child_handlers, spec), PROCESS_KINDS)
    register(app, sa)
    return sa


async def _json(request: Request) -> object:
    try:
        return await request.json()
    except ValueError:
        raise ApiError(400, "send a JSON body") from None


def register(app: FastAPI, sa: SettingsApi) -> None:
    @app.get("/api/system")
    def system():
        return sa.system()

    @app.get("/api/settings")
    def settings():
        return sa.current()

    @app.put("/api/settings")
    @app.post("/api/settings")  # the web client only issues GET, POST and DELETE
    async def put_settings(request: Request):
        return await run_in_threadpool(sa.update, await _json(request))

    @app.get("/api/mods/playlistmanager")
    def playlistmanager():
        return sa.mod.status()

    @app.post("/api/mods/playlistmanager/install")
    async def install_playlistmanager(request: Request):
        try:
            body = await request.json()
        except ValueError:
            body = None
        return await run_in_threadpool(sa.install_mod, body)
