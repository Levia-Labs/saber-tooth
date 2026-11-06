"""Writing output folders through LevelsWriter; never into an existing map folder."""

import json
import shutil
from pathlib import Path

from saber_tooth.map_folder_guard import named_refs
from saber_tooth.mapio import find_info, write_map
from saber_tooth.mapio.custom import READ_BY_NAME
from saber_tooth.model import Beatmap
from saber_tooth.safe_fs import LevelsWriter


def _referenced(partial: Path) -> set[str]:
    """Lower-cased file names the written Info.dat mentions; the only extras a fixed copy keeps."""
    info = json.loads(find_info(partial).read_text(encoding="utf-8"))
    return named_refs(info) | READ_BY_NAME


def _copy_tree(
    writer: LevelsWriter,
    src_root: Path,
    partial: Path,
    skip_dat: bool,
    only: set[str] | None = None,
) -> None:
    for src in sorted(p for p in src_root.rglob("*") if p.is_file() and not p.is_symlink()):
        dest = partial / src.relative_to(src_root)
        is_dat = src.suffix.lower() == ".dat" and src.name.lower() not in READ_BY_NAME
        if (skip_dat and is_dat) or dest.exists():
            continue
        if only is not None and dest.name.lower() not in only:
            continue
        writer.guard(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)


def write_fixed(levels: Path, original: Path, fixed: Beatmap, base: str) -> Path:
    """Write the fixed map to a new `<base>` folder, copying non-.dat files from the original."""
    writer = LevelsWriter(levels)
    name = writer.unique_name(base)
    partial = writer.new_folder(name)
    try:
        write_map(fixed, partial, original)
        _copy_tree(writer, original, partial, True, _referenced(partial))
        return writer.commit(partial, name)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise


def commit_staged(levels: Path, staging: Path, base: str) -> Path:
    writer = LevelsWriter(levels)
    name = writer.unique_name(base)
    partial = writer.new_folder(name)
    try:
        _copy_tree(writer, staging, partial, skip_dat=False)
        return writer.commit(partial, name)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise


def replace_fixed(levels: Path, original: Path, fixed: Beatmap, name: str) -> Path:
    """Write `fixed` as folder `name`, replacing the folder of that name left by an earlier save.

    The new copy is staged beside it first; the old one is only moved aside for the swap."""
    writer = LevelsWriter(levels)
    partial = writer.new_folder(name)
    target, old = levels / name, levels / f".{name}.old"
    try:
        write_map(fixed, partial, original)
        _copy_tree(writer, original, partial, True, _referenced(partial))
        if old.exists():
            shutil.rmtree(old)
        if target.exists():
            target.rename(old)
        partial.rename(target)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        if old.exists() and not target.exists():
            old.rename(target)
        raise
    shutil.rmtree(old, ignore_errors=True)
    return target
