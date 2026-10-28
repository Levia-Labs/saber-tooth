# Task 4: Worn check through OpenVR

Whether the headset is worn is readable only through SteamVR: the HMD's activity level, over a background OpenVR connection, while SteamVR runs. The optional `pyopenvr` module is loaded through an injected function, so tests pass a fake module and never touch SteamVR. User interaction means worn; idle or standby means not worn; every other level, a missing module, a closed SteamVR and any OpenVR error mean `None`. The monitor logs each failure kind once.

**Files:**

- Create: `src/saber_tooth/vr/worn.py`
- Modify: `src/saber_tooth/vr/README.md` (append one list item)
- Test: `tests/test_vr_worn.py`

**Interfaces:**

Consumes: nothing from earlier tasks.

Produces (`vr/worn.py`):

1. `worn_from_level(openvr, level: int) -> bool | None`: `True` for `k_EDeviceActivityLevel_UserInteraction`, `False` for `k_EDeviceActivityLevel_Idle` and `k_EDeviceActivityLevel_Standby`, else `None`. A constant the module does not define falls back to the OpenVR value (UserInteraction 1, Idle 0, Standby 3).
2. `WornMonitor(load: Callable[[], Any | None], log: Callable[[str], None])` with `read(steamvr_running: bool) -> bool | None`. It connects lazily with `openvr.init(openvr.VRApplication_Background)`, reads `getTrackedDeviceActivityLevel(openvr.k_unTrackedDeviceIndex_Hmd)`, closes the connection when SteamVR is not running or a read fails, and logs each failure kind (`missing`, `connect`, `read`) at most once.
3. `load_openvr() -> Any | None`: the `openvr` module, or None when it is not installed.
4. `stderr_log(message: str) -> None`: prints to standard error.

- [ ] **Step 1: Write the failing test**

Create `tests/test_vr_worn.py`:

```python
"""The worn check with a fake OpenVR module; SteamVR is never touched."""

from types import SimpleNamespace

from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.vr.worn import WornMonitor, worn_from_level


class FakeOpenVr(SimpleNamespace):
    """Stands in for pyopenvr: records init and shutdown, answers scripted activity levels."""

    def __init__(self, levels, init_error=None):
        super().__init__(
            k_EDeviceActivityLevel_UserInteraction=1,
            k_EDeviceActivityLevel_Idle=0,
            k_EDeviceActivityLevel_Standby=3,
            k_unTrackedDeviceIndex_Hmd=0,
            VRApplication_Background=3,
            levels=list(levels),
            init_error=init_error,
            inits=0,
            shutdowns=0,
            asked=[],
        )

    def init(self, kind):
        if self.init_error:
            raise self.init_error
        self.inits += 1
        outer = self

        class System:
            def getTrackedDeviceActivityLevel(self, index):
                outer.asked.append(index)
                level = outer.levels.pop(0)
                if isinstance(level, Exception):
                    raise level
                return level

        return System()

    def shutdown(self):
        self.shutdowns += 1


def monitor(fake):
    lines = []
    return WornMonitor(lambda: fake, lines.append), lines


def test_user_interaction_means_worn():
    fake = FakeOpenVr([1])
    mon, _ = monitor(fake)
    assert mon.read(True) is True
    assert fake.asked == [0]


def test_idle_and_standby_mean_not_worn():
    mon, _ = monitor(FakeOpenVr([0, 3]))
    assert mon.read(True) is False
    assert mon.read(True) is False


def test_every_other_level_is_unknown():
    mon, _ = monitor(FakeOpenVr([2, 4, -1, 99]))
    assert [mon.read(True) for _ in range(4)] == [None, None, None, None]


def test_the_connection_is_reused_between_reads():
    fake = FakeOpenVr([1, 0, 1])
    mon, _ = monitor(fake)
    assert [mon.read(True) for _ in range(3)] == [True, False, True]
    assert fake.inits == 1


def test_a_missing_module_is_unknown_and_logged_once():
    lines = []
    mon = WornMonitor(lambda: None, lines.append)
    assert [mon.read(True) for _ in range(3)] == [None, None, None]
    assert len(lines) == 1 and "pyopenvr" in lines[0]


def test_steamvr_closed_means_unknown_and_closes_the_connection_once():
    fake = FakeOpenVr([1])
    mon, _ = monitor(fake)
    assert mon.read(True) is True
    assert mon.read(False) is None
    assert mon.read(False) is None
    assert fake.shutdowns == 1


def test_a_read_error_is_unknown_logged_once_and_reconnects_next_time():
    fake = FakeOpenVr([RuntimeError("compositor gone"), RuntimeError("again"), 1])
    mon, lines = monitor(fake)
    assert mon.read(True) is None
    assert mon.read(True) is None
    assert mon.read(True) is True
    assert fake.inits == 3 and fake.shutdowns == 2
    assert len(lines) == 1 and "compositor gone" in lines[0]


def test_a_failed_connection_is_unknown_and_logged_once():
    fake = FakeOpenVr([], init_error=RuntimeError("VRInitError_Init_NoServerForBackgroundApp"))
    mon, lines = monitor(fake)
    assert [mon.read(True) for _ in range(3)] == [None, None, None]
    assert len(lines) == 1 and "NoServerForBackgroundApp" in lines[0]


def test_a_module_without_the_constants_uses_the_openvr_values():
    bare = SimpleNamespace()
    assert worn_from_level(bare, 1) is True
    assert worn_from_level(bare, 0) is False
    assert worn_from_level(bare, 3) is False
    assert worn_from_level(bare, 2) is None


@given(st.integers(-1000, 1000))
def test_only_levels_zero_one_and_three_are_known(level):
    expected = {1: True, 0: False, 3: False}.get(level)
    assert worn_from_level(FakeOpenVr([]), level) is expected
```

- [ ] **Step 2: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_vr_worn.py`
Expected: FAIL: `ModuleNotFoundError: No module named 'saber_tooth.vr.worn'`.

- [ ] **Step 3: Implement**

Create `src/saber_tooth/vr/worn.py`:

```python
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
```

Append to `src/saber_tooth/vr/README.md` (before the `Tests:` line):

```markdown
5. `worn.py`: `WornMonitor`, the optional pyopenvr worn check (background OpenVR connection, one log line per failure kind).
```

- [ ] **Step 4: Run it to see it pass**

Run: `rtk proxy uv run pytest -q tests/test_vr_worn.py`
Expected: PASS, 10 passed.

- [ ] **Step 5: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): worn check through an optional OpenVR connection" src/saber_tooth/vr tests/test_vr_worn.py`
