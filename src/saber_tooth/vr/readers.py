"""The real readers behind each probe. Tests never call these; they use fakes."""

import csv
import platform
import subprocess  # nosec B404 - fixed argv, no shell
from pathlib import Path

from saber_tooth.vr.probe import Readers

REGISTRY_KEY = r"SOFTWARE\Khronos\OpenXR\1"


def _csv_row(line: str) -> list[str]:
    """One quoted CSV line; blank text, INFO lines and an unterminated quote give no row."""
    text = line.strip()
    if len(text) < 2 or not (text.startswith('"') and text.endswith('"')):
        return []
    try:
        return next(csv.reader([text]))
    except (csv.Error, StopIteration):
        return []


def parse_tasklist(text: str) -> list[str]:
    """Image names (first column) from `tasklist /fo csv /nh`; malformed lines are skipped."""
    rows = (_csv_row(line) for line in text.splitlines())
    return [row[0] for row in rows if row and row[0]]


def windows_processes() -> list[str]:
    try:
        res = subprocess.run(  # nosec B603 B607 - constant argv, no shell
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_tasklist(res.stdout) if res.returncode == 0 else []


def windows_manifests() -> list[str]:
    """The `ActiveRuntime` registry value: the path of the active OpenXR runtime manifest."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGISTRY_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "ActiveRuntime")
    except OSError:
        return []
    return [value] if isinstance(value, str) else []


def read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _comm(entry: Path) -> str | None:
    """The process name in `entry/comm`, or None when the process is gone or unreadable."""
    try:
        return (entry / "comm").read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return None


def linux_comms(proc: Path = Path("/proc")) -> list[str]:
    names = [_comm(entry) for entry in proc.iterdir() if entry.name.isdigit()]
    return [name for name in names if name]


def linux_manifests(home: str | None = None) -> list[str]:
    root = Path(home) if home is not None else Path.home()
    user = (root / ".config" / "openxr" / "1" / "active_runtime.json").as_posix()
    return [user, "/etc/xdg/openxr/1/active_runtime.json"]


def detect_os(system: str | None = None) -> str:
    name = (platform.system() if system is None else system).strip().lower()
    return {"darwin": "macos", "": "unknown"}.get(name, name)


def default_readers(os_name: str) -> Readers:
    if os_name == "windows":
        return Readers(windows_processes, windows_manifests, read_text_file)
    if os_name == "linux":
        return Readers(linux_comms, linux_manifests, read_text_file)
    return Readers(lambda: [], lambda: [], read_text_file)
