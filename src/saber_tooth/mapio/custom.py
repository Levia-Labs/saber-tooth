"""Vanilla-safe Info.dat customData: what a fixed copy keeps from its source."""

import json
from pathlib import Path

from saber_tooth.mapio.errors import MapParseError

SAFE_KEYS = ("contributors", "editors")  # mod-only keys (requirements, environment removal) drop


READ_BY_NAME = frozenset({"bpminfo.dat"})  # files mapio opens by fixed name, not via Info.dat


def kept_custom(folder: Path) -> dict:
    """The harmless customData of `folder`'s Info.dat (v2 `_customData` or v4 `customData`),
    keyed in the v2 spelling; empty when the Info is missing, unreadable or has none."""
    from saber_tooth.mapio.discover import find_info  # discover imports write; avoid the cycle

    try:
        data = json.loads(find_info(folder).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, MapParseError):
        return {}
    if not isinstance(data, dict):
        return {}
    custom = data.get("_customData") or data.get("customData")
    if not isinstance(custom, dict):
        return {}
    kept = {}
    for key in SAFE_KEYS:
        for spelling in (f"_{key}", key):
            if spelling in custom:
                kept[f"_{key}"] = custom[spelling]
                break
    return kept
