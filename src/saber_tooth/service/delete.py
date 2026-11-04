"""Permanent removal of map folders, behind `Service.delete_map` and `Service.delete_maps`.

A delete never re-indexes the library: it drops the rows of the removed maps in one transaction
and re-indexes only the surviving members of the same chain (original and `[saber-tooth]` copies).
"""

import shutil
from pathlib import Path

from saber_tooth.copynames import is_fixed_copy, strip_fixed
from saber_tooth.map_folder_guard import check_map_folder
from saber_tooth.safe_fs import LevelsRoot, WriteRefused
from saber_tooth.service.errors import DeleteRefused, MapNotFound
from saber_tooth.store import Store


def _in_chain(name: str, base: str) -> bool:
    return name == base or (is_fixed_copy(name) and strip_fixed(name) == base)


def chain_members(names: list[str], removed: list[str]) -> list[str]:
    """Names among `names` in the same chain as any folder in `removed` (not those themselves)."""
    bases = {strip_fixed(r) for r in removed}
    gone = set(removed)
    return sorted(n for n in names if n not in gone and any(_in_chain(n, b) for b in bases))


class DeleteMixin:
    """`Service` methods that delete map folders from disk and their rows from the store."""

    levels: Path
    store: Store

    def reindex_folders(self, names: list[str]) -> int:
        raise NotImplementedError

    def _remove_folder(self, map_id: str, rows: list[dict]) -> str:
        """Guard, then remove one map folder; returns its name. Rows are left to the caller."""
        found = [m for m in rows if m["id"] == map_id]
        if not found:
            raise MapNotFound(f"unknown map: {map_id}")
        name = found[0]["folder"]
        try:
            folder = LevelsRoot(self.levels).guard(self.levels / name)
        except WriteRefused as exc:
            raise MapNotFound(f"map folder is gone: {name}") from exc
        if self.store.has_active_job(map_id):
            raise DeleteRefused(f"map {name} has a queued or running job")
        reasons = check_map_folder(self.levels / name, self.levels, map_id)
        if reasons:
            raise DeleteRefused(f"map {name} is not a deletable map folder: " + "; ".join(reasons))
        shutil.rmtree(folder)
        return name

    def _after_delete(self, ids: list[str], names: list[str]) -> None:
        """One transaction for the rows, then re-index the surviving chain members only."""
        self.store.delete_maps(ids)
        survivors = chain_members([m["folder"] for m in self.store.list_maps()], names)
        self.reindex_folders(survivors)

    def delete_map(self, map_id: str) -> dict:
        """Remove a map folder permanently; refused while a job is queued or running."""
        name = self._remove_folder(map_id, self.store.list_maps())
        self._after_delete([map_id], [name])
        return {"deleted": name}

    def delete_maps(self, ids: list[str]) -> dict:
        """Delete many maps; per-id status, never an abort; rows go in one transaction."""
        rows = self.store.list_maps()
        results, done, names = [], [], []
        for map_id in ids:
            try:
                names.append(self._remove_folder(map_id, rows))
                done.append(map_id)
                results.append({"id": map_id, "status": "deleted", "reasons": []})
            except MapNotFound as exc:
                results.append({"id": map_id, "status": "missing", "reasons": [str(exc)]})
            except DeleteRefused as exc:
                busy = "queued or running job" in str(exc)
                status = "busy" if busy else "refused"
                results.append({"id": map_id, "status": status, "reasons": [str(exc)]})
        if done:
            self._after_delete(done, names)
        return {"deleted": len(done), "results": results}
