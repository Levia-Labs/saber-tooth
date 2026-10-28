"""Permanent removal of a map folder, behind `Service.delete_map`."""

import shutil
from pathlib import Path

from saber_tooth.safe_fs import LevelsRoot, WriteRefused
from saber_tooth.service.errors import DeleteRefused, MapNotFound
from saber_tooth.store import Store


class DeleteMixin:
    """`Service` method that deletes a map folder from disk and its rows from the store."""

    levels: Path
    store: Store

    def refresh_library(self, wait: bool = True) -> int | None:
        raise NotImplementedError

    def delete_map(self, map_id: str) -> dict:
        """Remove a map folder permanently; refused while a job is queued or running."""
        rows = [m for m in self.store.list_maps() if m["id"] == map_id]
        if not rows:
            raise MapNotFound(f"unknown map: {map_id}")
        name = rows[0]["folder"]
        try:
            folder = LevelsRoot(self.levels).guard(self.levels / name)
        except WriteRefused as exc:
            raise MapNotFound(f"map folder is gone: {name}") from exc
        if self.store.has_active_job(map_id):
            raise DeleteRefused(f"map {name} has a queued or running job")
        shutil.rmtree(folder)
        self.store.delete_map(map_id)
        self.refresh_library()
        return {"deleted": name}
