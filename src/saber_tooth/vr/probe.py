"""One probe per OS. Every read goes through an injected reader, so tests pass fake data."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from saber_tooth.vr.model import Probe
from saber_tooth.vr.openxr import first_xr_name

WINDOWS_PROCESSES = {
    "ovrserver_x64.exe": "Oculus",
    "vrserver.exe": "SteamVR",
    "vrcompositor.exe": "SteamVR",
    "virtualdesktop.streamer.exe": "Virtual Desktop",
}
LINUX_PROCESSES = {
    "vrserver": "SteamVR",
    "monado-service": "Monado",
    "wivrn-server": "WiVRn",
}


@dataclass(frozen=True)
class Readers:
    """Everything a probe reads from the machine."""

    processes: Callable[[], Iterable[str]]
    manifests: Callable[[], Iterable[str]]
    read_text: Callable[[str], str]


def _names(read: Callable[[], Iterable[str]]) -> list[str]:
    """Strings from one reader; a reader that raises, or yields non-text, counts as empty."""
    try:
        return [item for item in read() if isinstance(item, str)]
    except Exception:
        return []


def _xr(readers: Readers) -> str | None:
    try:
        return first_xr_name(_names(readers.manifests), readers.read_text)
    except Exception:
        return None


def probe_windows(readers: Readers) -> Probe:
    names = (name.strip().lower() for name in _names(readers.processes))
    found = {WINDOWS_PROCESSES[name] for name in names if name in WINDOWS_PROCESSES}
    return Probe(sorted(found), _xr(readers))


def _linux_runtime(comm: str) -> str | None:
    name = comm.strip().lower()
    if name in LINUX_PROCESSES:
        return LINUX_PROCESSES[name]
    return "ALVR" if name.startswith("alvr") else None


def probe_linux(readers: Readers) -> Probe:
    found = {_linux_runtime(comm) for comm in _names(readers.processes)}
    return Probe(sorted(name for name in found if name), _xr(readers))


def probe_macos(readers: Readers) -> Probe:
    """No PC VR runtime exists on macOS, so nothing is read."""
    return Probe()


def probe(os_name: str, readers: Readers) -> Probe:
    """The probe for `os_name` (`windows`, `linux`, `macos`); any other name finds nothing."""
    if os_name == "windows":
        return probe_windows(readers)
    if os_name == "linux":
        return probe_linux(readers)
    if os_name == "macos":
        return probe_macos(readers)
    return Probe()
