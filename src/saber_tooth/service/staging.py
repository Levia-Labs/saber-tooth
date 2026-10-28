"""Startup sweep for generation staging folders a killed process left behind."""

import shutil
import time
from pathlib import Path

STALE_AFTER_S = 3600.0


def sweep_staging(data: Path, now: float | None = None) -> int:
    """Remove `data/staging/<id>` folders untouched for over an hour; returns how many went.
    Only direct child folders of the staging dir are considered; links are never followed."""
    root = Path(data) / "staging"
    if root.is_symlink() or not root.is_dir():
        return 0
    cutoff = (time.time() if now is None else now) - STALE_AFTER_S
    removed = 0
    for child in root.iterdir():
        try:
            if child.is_symlink() or not child.is_dir() or child.stat().st_mtime >= cutoff:
                continue
            shutil.rmtree(child)
            removed += 1
        except OSError:
            continue  # in use or already gone; the next start tries again
    return removed
