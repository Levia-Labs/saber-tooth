"""Download a BeatSaver zip, extract it safely and add it to CustomLevels as a new folder."""

import json
import re
import shutil
import stat
import threading
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from saber_tooth.beatsaver.client import BeatSaverClient, BeatSaverError, BeatSaverRateLimited
from saber_tooth.beatsaver.models import BsMap
from saber_tooth.beatsaver.naming import folder_name_for
from saber_tooth.mapio import MapParseError, load_map
from saber_tooth.safe_fs import LevelsWriter, WriteRefused, windows_safe_component
from saber_tooth.service.util import map_id_for

MAX_ZIP = 100 * 1024 * 1024
MAX_TOTAL = 400 * 1024 * 1024
MAX_ENTRIES = 500
MAX_DAT = 5 * 1024 * 1024
RATIO_FLOOR = 1024 * 1024
MAX_RATIO = 200
_INSTALL_LOCK = threading.Lock()
_DRIVE = re.compile(r"^[A-Za-z]:")
_UNSUPPORTED = ("noodle extensions", "mapping extensions")


class UnsafeArchive(ValueError):
    """The archive is corrupt or would write outside its folder."""


@dataclass(frozen=True)
class InstallOutcome:
    status: Literal["installed", "skipped", "failed"]
    reason: str | None = None
    folder: str | None = None
    rate_limited: bool = False


def _entry_path(info: zipfile.ZipInfo) -> PurePosixPath | None:
    """Validated relative path of an entry, or None for entries to ignore."""
    name = info.filename.replace("\\", "/")
    if not name or "\x00" in name or name.startswith("/") or _DRIVE.match(name):
        raise UnsafeArchive(f"unsafe path in archive: {info.filename!r}")
    path = PurePosixPath(name)
    if any(not windows_safe_component(part) for part in path.parts):
        raise UnsafeArchive(f"unsafe path in archive: {info.filename!r}")
    if path.parts and path.parts[0] == "__MACOSX":
        return None
    if stat.S_ISLNK(info.external_attr >> 16):
        raise UnsafeArchive(f"symlink in archive: {info.filename!r}")
    return path


def _ratio_ok(size: int, packed: int) -> bool:
    return size <= RATIO_FLOOR or size <= MAX_RATIO * max(packed, 1)


def _claim(path: PurePosixPath, is_dir: bool, files: set[str], dirs: set[str]) -> None:
    """Record a path under its casefolded NFC key; refuse case clashes and file/dir clashes."""
    key = unicodedata.normalize("NFC", str(path)).casefold()
    parts = key.split("/")
    ancestors = {"/".join(parts[:n]) for n in range(1, len(parts))}
    if key in files or ancestors & files or (not is_dir and key in dirs):
        raise UnsafeArchive(f"duplicate or clashing path in archive: {str(path)!r}")
    (dirs if is_dir else files).add(key)
    dirs |= ancestors


def _copy_limited(src, target: Path, budget: int, packed: int = 0) -> int:
    written = 0
    with target.open("wb") as out:
        while chunk := src.read(65536):
            written += len(chunk)
            if written > budget:
                raise UnsafeArchive("archive expands beyond the size limit")
            if not _ratio_ok(written, packed):
                raise UnsafeArchive("archive entry compression ratio is too high")
            out.write(chunk)
    return written


def safe_extract(zip_path: Path, dest: Path, max_total: int, max_entries: int) -> Path:
    """Extract into dest and return the folder holding Info.dat (one nested root is unwrapped)."""
    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise UnsafeArchive(f"not a readable zip: {type(exc).__name__}") from None
    with archive:
        infos = archive.infolist()
        if len(infos) > max_entries:
            raise UnsafeArchive("archive has too many entries")
        plan = [(i, _entry_path(i)) for i in infos]
        files: set[str] = set()
        dirs: set[str] = set()
        for i, p in plan:
            if p is not None:
                _claim(p, i.is_dir(), files, dirs)
            if p is not None and not i.is_dir() and not _ratio_ok(i.file_size, i.compress_size):
                raise UnsafeArchive("archive entry compression ratio is too high")
        if sum(i.file_size for i, p in plan if p and not i.is_dir()) > max_total:
            raise UnsafeArchive("archive expands beyond the size limit")
        dest.mkdir(parents=True, exist_ok=True)
        root = dest.resolve()
        used = 0
        try:
            for info, path in plan:
                if path is None:
                    continue
                target = (root / path).resolve()
                if root != target and root not in target.parents:
                    raise UnsafeArchive(f"unsafe path in archive: {info.filename!r}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src:
                    used += _copy_limited(src, target, max_total - used, info.compress_size)
        except (zipfile.BadZipFile, RuntimeError, OSError, EOFError) as exc:
            if isinstance(exc, UnsafeArchive):
                raise
            raise UnsafeArchive(f"corrupt archive: {type(exc).__name__}") from None
    return _map_root(root)


def _map_root(root: Path) -> Path:
    infos = [p for p in root.rglob("*") if p.is_file() and p.name.lower() == "info.dat"]
    if not infos:
        raise UnsafeArchive("archive has no Info.dat")
    if len(infos) > 1:
        raise UnsafeArchive("archive has more than one Info.dat")
    folder = infos[0].parent
    if len(folder.relative_to(root).parts) > 1:
        raise UnsafeArchive("Info.dat is nested too deeply")
    return folder


def _unsupported(folder: Path) -> str | None:
    """Reason when Info.dat requires Noodle or Mapping Extensions."""
    info = next((p for p in folder.iterdir() if p.name.lower() == "info.dat"), None)
    try:
        data = json.loads(info.read_text(encoding="utf-8-sig")) if info else None
    except RecursionError:
        raise UnsafeArchive("Info.dat is nested too deeply to parse") from None
    except (OSError, ValueError):
        return None
    found: list[str] = []

    def walk(node: object, requirement: bool) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, requirement or "requirement" in str(key).lower())
        elif isinstance(node, list):
            for value in node:
                walk(value, requirement)
        elif requirement and isinstance(node, str) and node.lower() in _UNSUPPORTED:
            found.append(node)

    try:
        walk(data, False)
    except RecursionError:
        raise UnsafeArchive("Info.dat is nested too deeply to parse") from None
    return f"requires {found[0]}, which is not supported" if found else None


def _check_dat_sizes(folder: Path) -> None:
    for path in folder.iterdir():
        if path.suffix.lower() == ".dat" and path.is_file() and path.stat().st_size > MAX_DAT:
            raise UnsafeArchive(f"{path.name} is larger than {MAX_DAT // 2**20} MB")


def _commit(writer: LevelsWriter, source: Path, bs: BsMap) -> str:
    name = writer.unique_name(folder_name_for(bs))
    partial = writer.new_folder(name)
    try:
        shutil.copytree(source, partial, dirs_exist_ok=True)
        return writer.commit(partial, name).name
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise


def install(
    client: BeatSaverClient,
    writer: LevelsWriter,
    store,
    bs: BsMap,
    tmp: Path,
    deadline: float | None = None,
) -> InstallOutcome:
    """Install one map as a new CustomLevels folder; never touches existing folders."""
    with _INSTALL_LOCK:
        return _install(client, writer, store, bs, tmp, deadline)


def _install(
    client: BeatSaverClient,
    writer: LevelsWriter,
    store,
    bs: BsMap,
    tmp: Path,
    deadline: float | None,
) -> InstallOutcome:
    try:
        folder_name_for(bs)  # validates the key before it is used in any path or query
        if store.find_bs(bs.id.lower(), bs.hash) is not None:
            return InstallOutcome("skipped", "already installed")
        work = tmp / f"bs-{bs.id.lower()}"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        try:
            archive = client.download(bs.download_url, work / "map.zip", MAX_ZIP, deadline)
            source = safe_extract(archive, work / "x", MAX_TOTAL, MAX_ENTRIES)
            _check_dat_sizes(source)
            reason = _unsupported(source)
            if reason:
                return InstallOutcome("failed", reason)
            load_map(source)
            name = _commit(writer, source, bs)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        mid = map_id_for(name)
        store.upsert_map(mid, name, bs.song_name or bs.name, bs.mapper, "", None)
        store.set_bs(mid, bs.id.lower(), bs.hash)
        return InstallOutcome("installed", None, name)
    except BeatSaverRateLimited as exc:
        return InstallOutcome("failed", str(exc), rate_limited=True)
    except RecursionError:
        return InstallOutcome("failed", "map data is nested too deeply to parse")
    except (BeatSaverError, UnsafeArchive, MapParseError, WriteRefused, ValueError, OSError) as exc:
        return InstallOutcome("failed", str(exc) or type(exc).__name__)
