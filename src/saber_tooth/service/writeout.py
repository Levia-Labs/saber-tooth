"""Writing output folders through LevelsWriter; never into an existing map folder."""

import shutil
from pathlib import Path

from saber_tooth.mapio import write_map
from saber_tooth.model import Beatmap
from saber_tooth.safe_fs import LevelsWriter


def _copy_tree(writer: LevelsWriter, src_root: Path, partial: Path, skip_dat: bool) -> None:
    for src in sorted(p for p in src_root.rglob("*") if p.is_file() and not p.is_symlink()):
        dest = partial / src.relative_to(src_root)
        if (skip_dat and src.suffix.lower() == ".dat") or dest.exists():
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
        _copy_tree(writer, original, partial, skip_dat=True)
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
