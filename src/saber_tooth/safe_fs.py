import shutil
from pathlib import Path


class WriteRefused(Exception):
    """Raised when a write would touch a pre-existing map folder."""


class LevelsWriter:
    """Writes new map folders under root; never into folders that already existed."""

    def __init__(self, root: Path):
        self.root = root
        self._existing = {p.resolve() for p in root.iterdir() if p.is_dir()}

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
        partial = self.root / f".{name}.partial"
        self.guard(partial)
        if partial.exists():
            shutil.rmtree(partial)
        partial.mkdir()
        return partial

    def commit(self, partial: Path, name: str) -> Path:
        target = self.root / name
        self.guard(target)
        if target.exists():
            raise WriteRefused(f"target already exists: {target}")
        partial.rename(target)
        return target
