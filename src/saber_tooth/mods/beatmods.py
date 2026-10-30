"""BeatMods (https://beatmods.com), the mod index ModAssistant uses.

`GET /api/mods?gameName=BeatSaber&gameVersion=V&status=verified&platform=universalpc` lists
`{"mods": [{"mod": {...}, "latest": {id, modVersion, zipHash, contentHashes, dependencies}}]}`;
`latest` is the newest build for that game version, and `dependencies` are build ids. A build's
zip is at `/cdn/mod/<zipHash>.zip`, and `zipHash` is its MD5. The client ignores proxy
variables, only talks to beatmods.com and never follows a redirect.
"""

import hashlib
import json
import re
from dataclasses import dataclass

import httpx

BASE = "https://beatmods.com"
GAME = "BeatSaber"
MAX_BYTES = 40 * 1024 * 1024
MAX_LIST_BYTES = 8 * 1024 * 1024
_HASH = re.compile(r"[0-9a-f]{32}")
_VERSION = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}")


class BeatModsError(Exception):
    """The mod index failed, answered nonsense or served a file that does not match its hash."""


class NoBuildError(BeatModsError):
    """The mod, or one of its dependencies, has no verified build for the game version."""


@dataclass(frozen=True)
class ModBuild:
    mod_id: int
    version_id: int
    name: str
    version: str
    zip_hash: str
    git_url: str | None
    files: dict[str, str]  # path inside the game folder -> MD5
    deps: tuple[int, ...]  # build ids
    size: int


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _build(item: object) -> ModBuild | None:
    if not isinstance(item, dict):
        return None
    mod, latest = item.get("mod"), item.get("latest")
    if not isinstance(mod, dict) or not isinstance(latest, dict):
        return None
    name, version, zip_hash = mod.get("name"), latest.get("modVersion"), latest.get("zipHash")
    if not (isinstance(name, str) and isinstance(version, str) and isinstance(zip_hash, str)):
        return None
    if not (_is_int(mod.get("id")) and _is_int(latest.get("id"))):
        return None
    if not _HASH.fullmatch(zip_hash):
        return None
    hashes = latest.get("contentHashes")
    files = {
        c["path"]: c["hash"]
        for c in (hashes if isinstance(hashes, list) else [])
        if isinstance(c, dict) and isinstance(c.get("path"), str) and isinstance(c.get("hash"), str)
    }
    raw_deps = latest.get("dependencies")
    deps = tuple(d for d in (raw_deps if isinstance(raw_deps, list) else []) if _is_int(d))
    git, size = mod.get("gitUrl"), latest.get("fileSize")
    return ModBuild(
        mod["id"],
        latest["id"],
        name,
        version,
        zip_hash,
        git if isinstance(git, str) else None,
        files,
        deps,
        size if _is_int(size) else 0,
    )


def parse_builds(payload: object) -> list[ModBuild]:
    """Every well-formed entry of a /api/mods answer; anything else is skipped."""
    items = payload.get("mods") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    return [b for b in map(_build, items) if b is not None]


def resolve(target: str, everything: list[ModBuild], for_game: list[ModBuild]) -> list[ModBuild]:
    """The target and its dependencies at the game's versions, dependencies first.

    Dependency ids point at builds that may belong to other game versions, so they are mapped
    to a mod through `everything` (the unfiltered list) and then to that mod's build in `for_game`.
    """
    mod_of = {b.version_id: b.mod_id for b in [*everything, *for_game]}
    by_mod = {b.mod_id: b for b in for_game}
    start = next((b for b in for_game if b.name == target), None)
    if start is None:
        raise NoBuildError(f"no build of {target} for this game version")
    ordered: list[ModBuild] = []
    seen: set[int] = set()

    def visit(build: ModBuild) -> None:
        seen.add(build.mod_id)
        for dep_id in build.deps:
            mod_id = mod_of.get(dep_id)
            if mod_id is None or mod_id in seen:
                continue
            dep = by_mod.get(mod_id)
            if dep is None:
                name = next((b.name for b in everything if b.mod_id == mod_id), str(mod_id))
                raise NoBuildError(f"no build of {name} for this game version")
            visit(dep)
        ordered.append(build)

    visit(start)
    return ordered


class BeatMods:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            base_url=BASE,
            timeout=httpx.Timeout(60.0, connect=10.0),
            trust_env=False,
            follow_redirects=False,
            headers={"User-Agent": "saber-tooth"},
        )

    def mods(self, game_version: str | None = None) -> list[ModBuild]:
        """Verified universal-PC builds, for one game version or the latest of every mod."""
        params = {"gameName": GAME, "status": "verified", "platform": "universalpc"}
        if game_version is not None:
            if not _VERSION.fullmatch(game_version):
                raise BeatModsError("unusable game version")
            params["gameVersion"] = game_version
        body = self._get("/api/mods", params, MAX_LIST_BYTES)
        try:
            return parse_builds(json.loads(body))
        except ValueError:
            raise BeatModsError("BeatMods answer was not JSON") from None

    def download(self, build: ModBuild, max_bytes: int = MAX_BYTES) -> bytes:
        """The build's zip, checked against its published MD5 before it is returned."""
        data = self._get(f"/cdn/mod/{build.zip_hash}.zip", None, max_bytes)
        if hashlib.md5(data).hexdigest() != build.zip_hash:  # noqa: S324 - the published hash
            raise BeatModsError(f"{build.name}: downloaded file does not match its published hash")
        return data

    def _get(self, path: str, params: dict | None, limit: int) -> bytes:
        try:
            with self._client.stream("GET", path, params=params) as response:
                if response.status_code != 200:
                    raise BeatModsError(f"BeatMods answered {response.status_code} for {path}")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > limit:
                        raise BeatModsError(f"{path} is larger than {limit} bytes")
                return bytes(body)
        except httpx.HTTPError as exc:
            raise BeatModsError(f"could not reach BeatMods: {exc}") from None
