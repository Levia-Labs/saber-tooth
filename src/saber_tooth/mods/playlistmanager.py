"""PlaylistManager status and install for the Beat Saber folder the service can reach.

Status is read from disk and from BeatMods (cached, fetched in the background); install
downloads the missing builds, verifies and checks them all, then writes only files that do not
exist yet. BSIPA, the mod loader, is a prerequisite: installing it needs a patch step this
service cannot run, so a missing BSIPA blocks the install and points at ModAssistant.
"""

import threading
import time
from collections.abc import Callable
from pathlib import Path

from saber_tooth.mods.beatmods import BeatMods, BeatModsError, ModBuild, NoBuildError, resolve
from saber_tooth.mods.extract import InstallError, mod_state, read_zip, write_new
from saber_tooth.mods.game import find_game, game_running, game_version
from saber_tooth.settings import Settings

GITHUB = "https://github.com/rithik-b/PlaylistManager"
TARGET = "PlaylistManager"
LOADER = "BSIPA"
TTL_S = 900.0
FAILED_TTL_S = 30.0
MOUNT_HELP = {
    "env": "GAME_DIR_HOST=<path to your Beat Saber folder>  (in .env next to docker-compose.yml)",
    "compose": [
        "environment:  GAME_DIR: ${GAME_DIR_HOST:+/game}",
        'volumes:      - "${GAME_DIR_HOST:-saber-game}:/game"',
    ],
    "then": "Run `docker compose up -d`, or enter the folder as the game path below.",
}


class PlaylistManagerMod:
    def __init__(
        self,
        settings: Settings,
        levels: Path,
        beatmods: Callable[[], BeatMods],
        env: str | None = None,
        running: Callable[[], bool | None] = game_running,
        background: bool = True,
    ) -> None:
        self._settings, self._levels, self._beatmods = settings, Path(levels), beatmods
        self._env, self._running, self._background = env, running, background
        self._lock = threading.Lock()
        self._cache: dict[str, dict] = {}  # game version -> catalogue result
        self._loading: set[str] = set()
        self._install_state = {"state": "idle", "message": None}

    # catalogue -----------------------------------------------------------------

    def _fetch(self, version: str) -> None:
        try:
            client = self._beatmods()
            plan = resolve(TARGET, client.mods(), client.mods(version))
            result = {"state": "ready", "error": None, "plan": plan}
        except NoBuildError as exc:
            result = {"state": "unsupported", "error": str(exc), "plan": []}
        except BeatModsError as exc:
            result = {"state": "failed", "error": str(exc), "plan": []}
        with self._lock:
            self._cache[version] = {**result, "at": time.monotonic()}
            self._loading.discard(version)

    def _catalog(self, version: str) -> dict:
        with self._lock:
            hit = self._cache.get(version)
            ttl = FAILED_TTL_S if hit and hit["state"] == "failed" else TTL_S
            fresh = hit is not None and time.monotonic() - hit["at"] < ttl
            if fresh or version in self._loading:
                return hit if fresh else {"state": "loading", "error": None, "plan": []}
            self._loading.add(version)
        if self._background:
            threading.Thread(target=self._fetch, args=(version,), daemon=True).start()
            return {"state": "loading", "error": None, "plan": []}
        self._fetch(version)
        return self._cache[version]

    # status --------------------------------------------------------------------

    def status(self) -> dict:
        folder = find_game(self._settings.game_dir(), self._env, self._levels)
        with self._lock:
            install = dict(self._install_state)
        base = {"github": GITHUB, "name": TARGET, "state": "unknown", "installed": False}
        if folder.root is None:
            mod = {**base, "can_install": False, "reason": "The game folder is not mounted."}
            return {
                "game": {
                    "state": "not_mounted",
                    "path": None,
                    "source": None,
                    "version": None,
                    "running": None,
                },
                "mount_help": MOUNT_HELP,
                "catalog": {"state": "idle", "error": None},
                "mod": mod,
                "install": install,
            }
        root, version = folder.root, game_version(folder.root)
        running = self._running()
        game = {
            "state": "ready",
            "path": str(root),
            "source": folder.source,
            "version": version,
            "running": running,
        }
        installed = (root / "Plugins" / "PlaylistManager.dll").is_file()
        mod = {**base, "installed": installed, "can_install": False}
        if version is None:
            mod["reason"] = "BeatSaberVersion.txt is missing or unreadable in the game folder."
            return {
                "game": game,
                "catalog": {"state": "idle", "error": None},
                "mod": mod,
                "install": install,
            }
        catalog = self._catalog(version)
        out = {
            "game": game,
            "catalog": {k: catalog[k] for k in ("state", "error")},
            "install": install,
        }
        if catalog["state"] == "ready":
            mod.update(self._mod_view(root, catalog["plan"], running, install))
        elif catalog["state"] == "unsupported":
            mod.update(
                state="unsupported",
                reason=f"No verified PlaylistManager build for Beat Saber {version}.",
            )
        return {**out, "mod": mod}

    def _mod_view(self, root: Path, plan: list[ModBuild], running, install: dict) -> dict:
        states = {b.name: mod_state(root, b) for b in plan}
        target = plan[-1]
        view = {
            "state": states[TARGET],
            "installed": states[TARGET] != "missing",
            "installed_version": target.version if states[TARGET] == "current" else None,
            "available_version": target.version,
            "dependencies": [
                {"name": b.name, "version": b.version, "state": states[b.name]} for b in plan[:-1]
            ],
        }
        view["reason"] = self._blocker(states, running, install)
        view["can_install"] = view["reason"] is None
        return view

    @staticmethod
    def _blocker(states: dict[str, str], running, install: dict) -> str | None:
        if install["state"] == "running":
            return "An install is already running."
        if running:
            return "Beat Saber is running; close it first."
        if all(s != "missing" for s in states.values()):
            return "PlaylistManager and its dependencies are already installed."
        if states.get(LOADER) == "missing":
            return "BSIPA, the mod loader, is not installed. Install it with ModAssistant first."
        return None

    # install -------------------------------------------------------------------

    def install(self) -> dict:
        """Start the install; refused with PermissionError when it cannot or should not run."""
        view = self.status()
        if view["game"]["state"] != "ready":
            raise PermissionError("The game folder is not mounted.")
        if view["catalog"]["state"] != "ready":
            raise PermissionError(view["mod"].get("reason") or "The mod list is not available yet.")
        if view["mod"].get("reason"):
            raise PermissionError(view["mod"]["reason"])
        root = Path(view["game"]["path"])
        plan = self._cache[view["game"]["version"]]["plan"]
        with self._lock:
            if self._install_state["state"] == "running":
                raise PermissionError("An install is already running.")
            self._install_state = {"state": "running", "message": "Downloading"}
        if self._background:
            threading.Thread(target=self._run, args=(root, plan), daemon=True).start()
        else:
            self._run(root, plan)
        return self.status()["install"]

    def _set(self, state: str, message: str | None) -> None:
        with self._lock:
            self._install_state = {"state": state, "message": message}

    def _run(self, root: Path, plan: list[ModBuild]) -> None:
        try:
            client = self._beatmods()
            todo = [b for b in plan if mod_state(root, b) == "missing"]
            files: list[tuple[str, bytes]] = []
            for build in todo:  # everything is fetched and checked before anything is written
                files += read_zip(build, client.download(build))
            if self._running():
                raise InstallError("Beat Saber is running; close it first.")
            self._set("running", "Writing files")
            write_new(root, files)
            names = ", ".join(f"{b.name} {b.version}" for b in todo)
            self._set("done", f"Installed {names}.")
        except (BeatModsError, InstallError) as exc:
            self._set("failed", str(exc))
        except Exception as exc:  # the worker thread must always end in a visible state
            self._set("failed", f"Install failed: {exc}")
