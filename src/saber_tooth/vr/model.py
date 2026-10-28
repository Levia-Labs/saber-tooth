"""The runtime order and the status shape the helper and the backend speak."""

from collections.abc import Iterable
from dataclasses import dataclass, field

RUNTIME_ORDER = ("SteamVR", "Oculus", "Virtual Desktop", "Monado", "WiVRn", "ALVR")


@dataclass(frozen=True)
class Probe:
    """What one OS probe found: runtime names in any order and the OpenXR runtime name."""

    runtimes: list[str] = field(default_factory=list)
    xr_runtime: str | None = None


def order_runtimes(found: Iterable[str]) -> list[str]:
    """Known runtimes in the fixed preference order, once each; unknown names are dropped."""
    seen = set(found)
    return [name for name in RUNTIME_ORDER if name in seen]


def status_dict(os_name: str, probe: Probe, worn: bool | None) -> dict:
    runtimes = order_runtimes(probe.runtimes)
    return {
        "os": os_name,
        "runtime": runtimes[0] if runtimes else None,
        "runtimes": runtimes,
        "xr_runtime": probe.xr_runtime,
        "worn": worn,
    }


def none_status(os_name: str = "unknown") -> dict:
    return status_dict(os_name, Probe(), None)
