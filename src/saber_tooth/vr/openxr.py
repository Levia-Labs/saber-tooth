"""The name of the active OpenXR runtime, read from its manifest."""

import json
import re
from collections.abc import Callable, Iterable


def xr_name(path: str, text: str) -> str | None:
    """`runtime.name` from the manifest `text`, else the manifest file name; None without a path."""
    if not path.strip():
        return None
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    runtime = data.get("runtime") if isinstance(data, dict) else None
    name = runtime.get("name") if isinstance(runtime, dict) else None
    if isinstance(name, str) and name.strip():
        return name.strip()
    return re.split(r"[\\/]", path.strip())[-1] or None


def _read(path: str, read_text: Callable[[str], str]) -> str | None:
    if not path.strip():
        return None
    try:
        return read_text(path)
    except (OSError, ValueError):
        return None


def first_xr_name(paths: Iterable[str], read_text: Callable[[str], str]) -> str | None:
    """The name for the first manifest that reads; a path whose file is missing is skipped."""
    for path in paths:
        text = _read(path, read_text)
        if text is not None:
            return xr_name(path, text)
    return None
