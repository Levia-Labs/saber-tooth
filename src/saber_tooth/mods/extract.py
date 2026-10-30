"""Read mod zips and write their files into Plugins, Libs and IPA of the game folder.

Nothing is written until every zip is downloaded, hash-checked and path-checked. Files are
created exclusively, so an existing file (an older or newer build, someone's own copy) is never
overwritten, and a failed write removes what this install created.
"""

import hashlib
import io
import zipfile
from pathlib import Path

from saber_tooth.mods.beatmods import ModBuild

ALLOWED_ROOTS = ("Plugins", "Libs", "IPA")
MAX_ENTRIES = 600
MAX_TOTAL_BYTES = 120 * 1024 * 1024


class InstallError(Exception):
    """A mod could not be installed; the message is shown to the user."""


def safe_entry(name: str) -> str | None:
    """The zip entry as a clean `Plugins|Libs|IPA/...` path, None for anything else."""
    if not name or "\x00" in name or "\\" in name or ":" in name or name.startswith("/"):
        return None
    parts = name.split("/")
    if len(parts) < 2 or parts[0] not in ALLOWED_ROOTS:
        return None
    if any(p in ("", ".", "..") for p in parts):
        return None
    return name


def read_zip(
    build: ModBuild, data: bytes, max_total: int = MAX_TOTAL_BYTES
) -> list[tuple[str, bytes]]:
    """(path, bytes) for every file in the zip, each checked against the published hashes."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise InstallError(f"{build.name}: the download is not a zip file") from None
    infos = archive.infolist()
    if len(infos) > MAX_ENTRIES or sum(i.file_size for i in infos) > max_total:
        raise InstallError(f"{build.name}: the zip is too large to install")
    out: list[tuple[str, bytes]] = []
    for info in infos:
        if info.is_dir():
            continue
        path = safe_entry(info.filename)
        if path is None:
            raise InstallError(f"{build.name}: the zip has a file outside Plugins, Libs and IPA")
        with archive.open(info) as handle:
            content = handle.read(info.file_size + 1)
        if len(content) != info.file_size:
            raise InstallError(f"{build.name}: the zip is damaged")
        published = build.files.get(path)
        if published and hashlib.md5(content).hexdigest() != published:  # noqa: S324
            raise InstallError(f"{build.name}: {path} does not match its published hash")
        out.append((path, content))
    return out


def _within(root: Path, path: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def write_new(root: Path, files: list[tuple[str, bytes]]) -> list[Path]:
    """Create each file that does not exist yet; returns what was created."""
    created: list[Path] = []
    try:
        for rel, content in files:
            if safe_entry(rel) is None:
                raise InstallError(f"refusing to write outside the mod folders: {rel}")
            dest = root / rel
            first = root / rel.split("/")[0]
            if first.is_symlink() or first.is_junction() or not _within(root, dest.parent):
                raise InstallError(f"{rel.split('/')[0]} is a link; refusing to write through it")
            if dest.exists() or dest.is_symlink():
                continue  # never overwrite: it may be a newer build
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as handle:
                created.append(dest)
                handle.write(content)
    except InstallError:
        _undo(created)
        raise
    except OSError as exc:
        _undo(created)
        raise InstallError(
            f"could not write to the game folder ({exc.strerror or exc}); "
            "close Beat Saber and check the folder is writable"
        ) from None
    return created


def _undo(created: list[Path]) -> None:
    for path in reversed(created):
        path.unlink(missing_ok=True)


def mod_state(root: Path, build: ModBuild) -> str:
    """`current` when the mod's DLLs match the published build, `other` when a DLL differs
    (another version, possibly newer), `missing` when a DLL is absent."""
    dlls = {p: h for p, h in build.files.items() if p.lower().endswith(".dll") and safe_entry(p)}
    state = "current" if dlls else "missing"
    for rel, published in dlls.items():
        target = root / rel
        if not target.is_file():
            state = "missing" if state == "current" else state
            continue
        try:
            actual = hashlib.md5(target.read_bytes()).hexdigest()  # noqa: S324
        except OSError:
            return "other"
        if actual != published:
            return "other"
    return state
