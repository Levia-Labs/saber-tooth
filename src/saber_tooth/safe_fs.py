import re
import shutil
from pathlib import Path

_BAD_CHARS = re.compile(r'[\x00-\x1f\x7f-\x9f<>:"|?*]')
_RESERVED = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{n}" for n in "123456789¹²³"}
    | {f"lpt{n}" for n in "123456789¹²³"}
)


def windows_safe_component(name: str) -> bool:
    """True when `name` is a legal single path component on Windows NTFS.

    Rejects empty names, `.`/`..`, separators, ':' (alternate data streams), control
    characters, `<>"|?*`, a trailing '.' or ' ' and reserved device names (CON, NUL,
    COM1-9, LPT1-9 ...) with or without an extension, case-insensitively.
    """
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        return False
    if _BAD_CHARS.search(name) or name[-1] in ". ":
        return False
    return name.split(".", 1)[0].rstrip(" ").casefold() not in _RESERVED


class WriteRefused(Exception):
    """Raised when a write would touch a pre-existing map folder."""


class LevelsRoot:
    """A levels directory; `guard` accepts only real, direct child folders of it."""

    def __init__(self, root: Path):
        self.root = root

    def guard(self, path: Path) -> Path:
        """Return `path` when it is a non-symlink directory directly under the root."""
        # Junctions are Windows directory links that is_symlink() does not report.
        if path.is_symlink() or path.is_junction() or not path.is_dir():
            raise WriteRefused(f"not a map folder: {path}")
        if path.resolve().parent != self.root.resolve():
            raise WriteRefused(f"not a direct child of the levels folder: {path}")
        return path


class LevelsWriter:
    """Writes new map folders under root; never into folders that already existed."""

    def __init__(self, root: Path):
        self.root = root
        self._existing = {
            p.resolve()
            for p in root.iterdir()
            if p.is_dir() and not (p.name.startswith(".") and p.name.endswith(".partial"))
        }

    def guard(self, path: Path) -> None:
        resolved = path.resolve()
        for folder in self._existing:
            if folder == resolved or folder in resolved.parents:
                raise WriteRefused(f"refusing to write inside existing map folder: {folder}")

    def unique_name(self, base: str) -> str:
        if not (self.root / base).exists():
            return base
        stem, suffix = (base[:-1], "]") if base.endswith("]") else (base, "")
        n = 2
        while (self.root / f"{stem} {n}{suffix}").exists():
            n += 1
        return f"{stem} {n}{suffix}"

    def new_folder(self, name: str) -> Path:
        if not windows_safe_component(name):
            raise WriteRefused(f"unsafe folder name: {name!r}")
        partial = self.root / f".{name}.partial"
        self.guard(partial)
        if partial.exists():
            shutil.rmtree(partial)
        partial.mkdir()
        return partial

    def commit(self, partial: Path, name: str) -> Path:
        if not windows_safe_component(name):
            raise WriteRefused(f"unsafe folder name: {name!r}")
        target = self.root / name
        self.guard(target)
        if target.exists():
            raise WriteRefused(f"target already exists: {target}")
        partial.rename(target)
        return target
