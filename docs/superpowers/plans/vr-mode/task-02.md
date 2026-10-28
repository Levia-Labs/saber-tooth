# Task 2: Windows and macOS probes with injected readers

A probe never reads the machine itself: it takes a `Readers` bundle, so tests pass fake process lists and fake manifests. A reader that raises counts as empty, so one broken source never hides the others. This task adds the Windows and macOS probes, the dispatcher, and the Windows readers (`tasklist` output parser and the registry read). Linux follows in Task 3.

**Files:**

- Create: `src/saber_tooth/vr/probe.py`
- Create: `src/saber_tooth/vr/readers.py`
- Modify: `src/saber_tooth/vr/README.md` (append two list items)
- Test: `tests/test_vr_probe_windows.py`

**Interfaces:**

Consumes: `Probe` (`vr/model.py`), `first_xr_name` (`vr/openxr.py`), both Task 1.

Produces (`vr/probe.py`):

1. `WINDOWS_PROCESSES: dict[str, str]`: lower-case image name to runtime: `ovrserver_x64.exe` Oculus, `vrserver.exe` and `vrcompositor.exe` SteamVR, `virtualdesktop.streamer.exe` Virtual Desktop.
2. `Readers(processes: Callable[[], Iterable[str]], manifests: Callable[[], Iterable[str]], read_text: Callable[[str], str])`: frozen dataclass. `processes` yields process names, `manifests` yields candidate OpenXR manifest paths in preference order, `read_text` reads one path and raises `OSError` when it cannot.
3. `probe_windows(readers: Readers) -> Probe`, `probe_macos(readers: Readers) -> Probe` (always empty, reads nothing), `probe(os_name: str, readers: Readers) -> Probe` (`"windows"`, `"macos"`, anything else empty; `"linux"` is added in Task 3).

Produces (`vr/readers.py`):

1. `parse_tasklist(text: str) -> list[str]`: image names from `tasklist /fo csv /nh` output; blank and malformed lines are skipped.
2. `windows_processes() -> list[str]`: runs `tasklist /fo csv /nh` and parses it; an empty list when it fails.
3. `windows_manifests() -> list[str]`: the `ActiveRuntime` value under `HKLM\SOFTWARE\Khronos\OpenXR\1`; empty when the key is absent.
4. `read_text_file(path: str) -> str`: UTF-8 text of one file.

- [ ] **Step 1: Write the failing test**

Create `tests/test_vr_probe_windows.py`:

```python
"""The Windows and macOS probes with fake process lists and fake manifests."""

import json

import pytest

from saber_tooth.vr.model import status_dict
from saber_tooth.vr.probe import Readers, probe, probe_macos, probe_windows
from saber_tooth.vr.readers import parse_tasklist


def readers(processes=(), manifests=(), files=None):
    files = files or {}

    def read_text(path):
        if path not in files:
            raise FileNotFoundError(path)
        return files[path]

    return Readers(lambda: list(processes), lambda: list(manifests), read_text)


def boom():
    raise OSError("unreadable")


def test_oculus_service_means_oculus():
    found = probe_windows(readers(["explorer.exe", "OVRServer_x64.exe"]))
    assert found.runtimes == ["Oculus"]


def test_steamvr_counts_once_for_server_and_compositor():
    found = probe_windows(readers(["vrserver.exe", "vrcompositor.exe"]))
    assert found.runtimes == ["SteamVR"]


def test_virtual_desktop_streamer_is_detected():
    found = probe_windows(readers(["VirtualDesktop.Streamer.exe"]))
    assert found.runtimes == ["Virtual Desktop"]


def test_windows_process_names_match_case_insensitively_and_ignore_padding():
    names = [" ovrserver_x64.EXE ", "VRSERVER.EXE"]
    assert sorted(probe_windows(readers(names)).runtimes) == ["Oculus", "SteamVR"]


def test_nothing_running_means_no_runtime():
    assert probe_windows(readers(["explorer.exe", "chrome.exe"])).runtimes == []
    assert status_dict("windows", probe_windows(readers()), None)["runtime"] is None


def test_openxr_runtime_comes_from_the_registry_manifest():
    path = "C:\\Program Files\\Oculus\\Support\\oculus-runtime\\oculus_openxr_64.json"
    files = {path: json.dumps({"runtime": {"name": "Oculus"}})}
    assert probe_windows(readers(manifests=[path], files=files)).xr_runtime == "Oculus"


def test_a_registry_entry_pointing_at_a_missing_file_gives_no_xr_runtime():
    assert probe_windows(readers(manifests=["C:\\gone.json"])).xr_runtime is None


def test_an_unreadable_process_list_still_reads_the_openxr_manifest():
    files = {"C:\\a.json": json.dumps({"runtime": {"name": "SteamVR"}})}
    found = probe_windows(Readers(boom, lambda: ["C:\\a.json"], readers(files=files).read_text))
    assert found.runtimes == [] and found.xr_runtime == "SteamVR"


def test_an_unreadable_manifest_source_still_reports_processes():
    found = probe_windows(Readers(lambda: ["vrserver.exe"], boom, readers().read_text))
    assert found.runtimes == ["SteamVR"] and found.xr_runtime is None


def test_non_text_process_entries_are_ignored():
    found = probe_windows(
        Readers(lambda: [None, 7, "vrserver.exe"], lambda: [], readers().read_text)
    )
    assert found.runtimes == ["SteamVR"]


def test_macos_has_no_runtime_and_reads_nothing():
    def fail():
        raise AssertionError("macOS must not read the machine")

    found = probe_macos(Readers(fail, fail, lambda path: fail()))
    assert found.runtimes == [] and found.xr_runtime is None


@pytest.mark.parametrize("name", ["freebsd", "", "plan9", "unknown"])
def test_an_unknown_os_probes_to_nothing(name):
    found = probe(name, readers(["vrserver.exe", "vrserver"]))
    assert found.runtimes == [] and found.xr_runtime is None


def test_dispatch_routes_windows_and_macos():
    assert probe("windows", readers(["vrserver.exe"])).runtimes == ["SteamVR"]
    assert probe("macos", readers(["vrserver.exe"])).runtimes == []


TASKLIST = (
    '"System Idle Process","0","Services","0","8 K"\n'
    '"OVRServer_x64.exe","4120","Console","1","120,000 K"\n'
    "\n"
    "INFO: garbage line without quotes\n"
    '"vrserver.exe","5580","Console","1","90,000 K"\n'
)


def test_parse_tasklist_takes_the_image_name_column():
    assert parse_tasklist(TASKLIST) == ["System Idle Process", "OVRServer_x64.exe", "vrserver.exe"]


def test_parse_tasklist_on_empty_or_broken_text():
    assert parse_tasklist("") == []
    assert parse_tasklist('"unterminated,1\n') == []
```

- [ ] **Step 2: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_vr_probe_windows.py`
Expected: FAIL: `ModuleNotFoundError: No module named 'saber_tooth.vr.probe'`.

- [ ] **Step 3: Implement**

Create `src/saber_tooth/vr/probe.py`:

```python
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


def probe_macos(readers: Readers) -> Probe:
    """No PC VR runtime exists on macOS, so nothing is read."""
    return Probe()


def probe(os_name: str, readers: Readers) -> Probe:
    """The probe for `os_name` (`windows`, `macos`); any other name finds nothing."""
    if os_name == "windows":
        return probe_windows(readers)
    if os_name == "macos":
        return probe_macos(readers)
    return Probe()
```

Create `src/saber_tooth/vr/readers.py`:

```python
"""The real readers behind each probe. Tests never call these; they use fakes."""

import csv
import subprocess  # nosec B404 - fixed argv, no shell
from pathlib import Path

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
```

Append to `src/saber_tooth/vr/README.md` (before the `Tests:` line):

```markdown
3. `probe.py`: `Readers`, one probe per OS (`probe_windows`, `probe_macos`) and `probe(os_name, readers)`.
4. `readers.py`: the real readers (`tasklist`, the OpenXR registry value, file text).
```

- [ ] **Step 4: Run it to see it pass**

Run: `rtk proxy uv run pytest -q tests/test_vr_probe_windows.py`
Expected: PASS, 18 passed.

- [ ] **Step 5: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): Windows and macOS probes with injected readers" src/saber_tooth/vr tests/test_vr_probe_windows.py`
