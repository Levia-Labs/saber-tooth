"""Where the Beat Saber install is, which version it is, and whether the game is running."""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from saber_tooth.settings import GAME_MARKERS

VERSION_FILE = "BeatSaberVersion.txt"
_VERSION = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}")
EXE_NAMES = ("beat saber.exe", "beat saber")


@dataclass(frozen=True)
class GameFolder:
    root: Path | None
    source: str | None  # "setting", "env" or "levels"


def _is_game(path: Path | None) -> bool:
    try:
        return path is not None and path.is_dir() and any((path / m).exists() for m in GAME_MARKERS)
    except OSError:
        return False


def find_game(setting: Path | None, env: str | None, levels: Path) -> GameFolder:
    """The install root: the saved setting, then GAME_DIR, then two folders above CustomLevels."""
    derived = levels.parent.parent if levels.parent.name == "Beat Saber_Data" else None
    for source, candidate in (
        ("setting", setting),
        ("env", Path(env) if env else None),
        ("levels", derived),
    ):
        if _is_game(candidate):
            return GameFolder(candidate, source)
    return GameFolder(None, None)


def game_version(root: Path) -> str | None:
    """The version in BeatSaberVersion.txt, None when absent or not plain major.minor.patch."""
    try:
        text = (root / VERSION_FILE).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return text if _VERSION.fullmatch(text) else None


def _process_names() -> list[str] | None:
    """Names of running processes, None where the platform cannot list them."""
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10, check=True,
            ).stdout  # fmt: skip
            return [line.split('","')[0].strip('"') for line in out.splitlines() if line]
        names = []
        for comm in Path("/proc").glob("[0-9]*/comm"):
            try:
                names.append(comm.read_text(encoding="utf-8").strip())
            except OSError:
                continue
        return names or None
    except (OSError, subprocess.SubprocessError):
        return None


def game_running() -> bool | None:
    """True when a Beat Saber process is visible, None when processes cannot be listed.

    A container sees only its own processes, so False there does not rule out a running game.
    """
    names = _process_names()
    if names is None:
        return None
    return any(n.lower() in EXE_NAMES for n in names)
