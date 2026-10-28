"""Swap a staged cropped folder in for the original map folder, with a rollback on any failure."""

import logging
import shutil
from pathlib import Path

from saber_tooth.safe_fs import LevelsRoot, WriteRefused

log = logging.getLogger(__name__)


def replace_folder(levels: Path, original: Path, partial: Path) -> Path:
    """Make `partial` the folder `original`.

    The original must pass `LevelsRoot.guard`. It is renamed to a temporary sibling, the partial is
    renamed to the original name and only then is the temporary original removed. When either
    rename fails the original is put back and the partial is removed.
    """
    try:
        LevelsRoot(levels).guard(original)
    except WriteRefused:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    aside = original.with_name(f".{original.name}.old.partial")
    try:
        if aside.exists():
            shutil.rmtree(aside)
        original.rename(aside)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    try:
        partial.rename(original)
    except BaseException:
        aside.rename(original)
        shutil.rmtree(partial, ignore_errors=True)
        raise
    shutil.rmtree(aside, ignore_errors=True)
    if aside.exists():
        log.warning("could not remove the replaced folder %s", aside)
    return original
