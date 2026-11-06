"""Show a container path as the host path it is mounted from (`LEVELS_DIR_HOST`)."""

import re

_WINDOWS = re.compile(r"[A-Za-z]:[\\/]|\\\\")


def host_path(path: str, levels: str, host: str | None) -> str:
    """Swap the `levels` prefix of `path` for `host`; only whole segments match.

    A Windows host path (drive letter or UNC) comes back with backslashes throughout.
    """
    if not host:
        return path
    base = levels.replace("\\", "/").rstrip("/")
    norm = path.replace("\\", "/") if "\\" in levels else path
    if norm == base:
        rest = ""
    elif norm.startswith(base + "/"):
        rest = norm[len(base) + 1 :]
    else:
        return path
    if _WINDOWS.match(host):
        root = host.replace("/", "\\").rstrip("\\")
        return root + "\\" + rest.replace("/", "\\") if rest else root
    root = host.rstrip("/") or "/"
    if not rest:
        return root
    return root + rest if root == "/" else f"{root}/{rest}"
