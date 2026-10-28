"""Is the headset worn? Read through the optional pyopenvr package while SteamVR runs."""

import sys
import threading
from collections.abc import Callable
from typing import Any

# OpenVR EDeviceActivityLevel values, used when the module does not name the constant.
_DEFAULTS = {"UserInteraction": 1, "Idle": 0, "Standby": 3}


def _level(openvr: Any, name: str) -> int:
    return getattr(openvr, f"k_EDeviceActivityLevel_{name}", _DEFAULTS[name])


def worn_from_level(openvr: Any, level: int) -> bool | None:
    """True on user interaction, False on idle or standby, None for every other level."""
    if level == _level(openvr, "UserInteraction"):
        return True
    if level in (_level(openvr, "Idle"), _level(openvr, "Standby")):
        return False
    return None


def load_openvr() -> Any | None:
    try:
        import openvr
    except ImportError:
        return None
    return openvr


def stderr_log(message: str) -> None:
    print(message, file=sys.stderr)


class WornMonitor:
    """Keeps one background OpenVR connection while SteamVR runs and reads the HMD from it."""

    def __init__(self, load: Callable[[], Any | None], log: Callable[[str], None]):
        self._load = load
        self._log = log
        self._lock = threading.Lock()
        self._openvr: Any | None = None
        self._system: Any | None = None
        self._logged: set[str] = set()

    def _once(self, kind: str, message: str) -> None:
        if kind not in self._logged:
            self._logged.add(kind)
            self._log(message)

    def _connect(self) -> bool:
        if self._openvr is None:
            self._openvr = self._load()
        if self._openvr is None:
            self._once("missing", "worn: pyopenvr is not installed; worn stays unknown")
            return False
        try:
            self._system = self._openvr.init(self._openvr.VRApplication_Background)
        except Exception as exc:
            self._once("connect", f"worn: could not connect to SteamVR ({exc}); worn stays unknown")
            return False
        return True

    def _close(self) -> None:
        if self._system is None or self._openvr is None:
            return
        self._system = None
        try:
            self._openvr.shutdown()
        except Exception as exc:
            self._once("close", f"worn: closing the OpenVR connection failed ({exc})")

    def read(self, steamvr_running: bool) -> bool | None:
        with self._lock:
            if not steamvr_running:
                self._close()
                return None
            if self._system is None and not self._connect():
                return None
            try:
                level = self._system.getTrackedDeviceActivityLevel(
                    self._openvr.k_unTrackedDeviceIndex_Hmd
                )
            except Exception as exc:
                self._close()
                self._once("read", f"worn: reading the headset failed ({exc}); worn stays unknown")
                return None
            return worn_from_level(self._openvr, level)
