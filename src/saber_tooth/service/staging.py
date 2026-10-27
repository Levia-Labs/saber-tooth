"""Removal of staging folders whose proposals are all settled."""

import shutil
from pathlib import Path

from saber_tooth.store import Store


def clean_staging(root: Path, store: Store, prefix: str) -> None:
    if not root.is_dir():
        return
    for d in root.iterdir():
        props = store.proposals(f"{prefix}{d.name}")
        if props and all(p["status"] in ("rejected", "applied") for p in props):
            shutil.rmtree(d, ignore_errors=True)
