"""Rename a map: new song name in Info.dat, new folder name, store rows moved to the new id."""

import json
import re
from pathlib import Path

from saber_tooth.safe_fs import LevelsRoot, WriteRefused, windows_safe_component
from saber_tooth.service.errors import MapNotFound, RenameConflict, RenameInvalid
from saber_tooth.service.util import map_id_for
from saber_tooth.store import Store
from saber_tooth.store_maps import FIXED_COPY_SUFFIX as SUFFIX

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
        """Rename a map folder and its song name; returns the new map id.

        A fixed copy keeps its " [saber-tooth]" folder suffix and its original follows it (and an
        original takes its copy along), because the pairing is `<original folder>` + the suffix.
        """
        name, base = validate_map_name(raw_name)
        base = base.removesuffix(SUFFIX).rstrip(". ") or base
        by_id = {m["id"]: m["folder"] for m in self.store.list_maps()}
        if map_id not in by_id:
            raise MapNotFound(f"unknown map: {map_id}")
        old_name = by_id[map_id]
        is_copy = old_name.endswith(SUFFIX)
        old_base = old_name.removesuffix(SUFFIX) if is_copy else old_name
        pair = (old_base if is_copy else old_name + SUFFIX) in by_id.values()
        moves = [(old_name, base + SUFFIX if is_copy else base)]
        if pair:
            moves.append((old_base, base) if is_copy else (old_name + SUFFIX, base + SUFFIX))
        moves = [(a, b) for a, b in moves if a != b]
        ids = {m["folder"]: m["id"] for m in self.store.list_maps()}
        root = LevelsRoot(self.levels)
        try:
            folders = {a: root.guard(self.levels / a) for a in {old_name, *(a for a, _ in moves)}}
        except WriteRefused as exc:
            raise MapNotFound(f"map folder is gone: {old_name}") from exc
        for a, b in moves:
            if self.store.has_active_job(ids[a]):
                raise RenameConflict(f"map {a} has a queued or running job")
            target = self.levels / b
            if target.exists() and not (
                a.casefold() == b.casefold() and target.samefile(folders[a])
            ):
                raise RenameConflict(f"a folder named {b} already exists")
        done: list[tuple[str, str]] = []
        try:
            for a, b in moves:
                folders[a].rename(self.levels / b)
                done.append((a, b))
            _write_song_name(self.levels / dict(moves).get(old_name, old_name), name)
        except Exception:
            for a, b in reversed(done):
                (self.levels / b).rename(self.levels / a)
            raise
        for a, b in done:
            if map_id_for(b) != ids[a]:
                self.store.rename_map(ids[a], map_id_for(b))
        self.refresh_library()
        return map_id_for(dict(moves).get(old_name, old_name))
