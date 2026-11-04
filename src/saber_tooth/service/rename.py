"""Rename a map: new song name in Info.dat, new folder name, store rows moved to the new id."""

import json
import re
from pathlib import Path

from saber_tooth.safe_fs import LevelsRoot, WriteRefused, windows_safe_component
from saber_tooth.service.errors import MapNotFound, RenameConflict, RenameInvalid
from saber_tooth.service.util import map_id_for
from saber_tooth.store import Store

MAX_NAME = 120
_FOLDER_STRIP = re.compile(r'[\x00-\x1f\x7f-\x9f<>:"|?*/\\]')


def validate_map_name(raw: object) -> tuple[str, str]:
    """Return (song name, safe folder name) for a requested name, or raise RenameInvalid."""
    if not isinstance(raw, str):
        raise RenameInvalid("name must be text")
    name = raw.strip()
    if not name or len(name) > MAX_NAME:
        raise RenameInvalid(f"name must be 1-{MAX_NAME} characters")
    if "/" in name or "\\" in name:
        raise RenameInvalid("name must not contain a path separator")
    if any(ord(c) < 32 or 0x7F <= ord(c) <= 0x9F for c in name):
        raise RenameInvalid("name must not contain control characters")
    folder = " ".join(_FOLDER_STRIP.sub("", name).split()).rstrip(". ")
    if not windows_safe_component(folder):
        raise RenameInvalid("name cannot be used as a folder name")
    return name, folder


def _info_file(folder: Path) -> Path:
    for p in folder.iterdir():
        if p.is_file() and p.name.lower() == "info.dat":
            return p
    raise MapNotFound(f"map has no Info.dat: {folder.name}")


def _write_song_name(folder: Path, name: str) -> None:
    path = _info_file(folder)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data.get("song"), dict):  # v4
        data["song"]["title"] = name
    else:
        data["_songName"] = name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class RenameMixin:
    levels: Path
    store: Store

    def refresh_library(self, wait: bool = True) -> int | None:
        raise NotImplementedError

    def rename_map(self, map_id: str, raw_name: object) -> str:
        """Rename a map folder and its song name; returns the new map id."""
        name, target_name = validate_map_name(raw_name)
        rows = [m for m in self.store.list_maps() if m["id"] == map_id]
        if not rows:
            raise MapNotFound(f"unknown map: {map_id}")
        old_name = rows[0]["folder"]
        try:
            folder = LevelsRoot(self.levels).guard(self.levels / old_name)
        except WriteRefused as exc:
            raise MapNotFound(f"map folder is gone: {old_name}") from exc
        if self.store.has_active_job(map_id):
            raise RenameConflict(f"map {old_name} has a queued or running job")
        target = self.levels / target_name
        moved = target_name != old_name
        if moved:
            if target.exists() and not (
                target.name.casefold() == old_name.casefold() and target.samefile(folder)
            ):
                raise RenameConflict(f"a folder named {target_name} already exists")
            folder.rename(target)
        try:
            _write_song_name(target if moved else folder, name)
        except Exception:
            if moved:
                target.rename(folder)
            raise
        new_id = map_id_for(target_name)
        if new_id != map_id:
            self.store.rename_map(map_id, new_id)
        self.refresh_library()
        return new_id
