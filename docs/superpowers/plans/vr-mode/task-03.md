# Task 3: Linux probe, OS detection and the default readers

Linux reads `/proc/*/comm`; a process can exit between the directory listing and the read, and a `comm` file can be unreadable, so each entry is read on its own and a failed one is skipped. The OpenXR runtime comes from `~/.config/openxr/1/active_runtime.json`, else `/etc/xdg/openxr/1/active_runtime.json`.

**Files:**

- Modify: `src/saber_tooth/vr/probe.py`
- Modify: `src/saber_tooth/vr/readers.py`
- Test: `tests/test_vr_probe_linux.py`

**Interfaces:**

Consumes: `Readers`, `probe` (Task 2), `Probe`, `first_xr_name` (Task 1).

Produces (`vr/probe.py`):

1. `LINUX_PROCESSES: dict[str, str]`: `vrserver` SteamVR, `monado-service` Monado, `wivrn-server` WiVRn. A name starting with `alvr` (any case) is ALVR.
2. `probe_linux(readers: Readers) -> Probe`; `probe("linux", readers)` now routes to it.

Produces (`vr/readers.py`):

1. `linux_comms(proc: Path = Path("/proc")) -> list[str]`: the `comm` of every numeric entry under `proc`; entries that vanish or cannot be read are skipped.
2. `linux_manifests(home: str | None = None) -> list[str]`: `[<home>/.config/openxr/1/active_runtime.json, /etc/xdg/openxr/1/active_runtime.json]` as POSIX paths; `home` defaults to the user's home directory.
3. `detect_os(system: str | None = None) -> str`: `"windows"`, `"linux"`, `"macos"` (from `Darwin`) or the lower-cased name; `system` defaults to `platform.system()`.
4. `default_readers(os_name: str) -> Readers`: the real readers for `windows` and `linux`; empty process and manifest readers for any other name.

- [ ] **Step 1: Write the failing test**

Create `tests/test_vr_probe_linux.py`:

```python
"""The Linux probe, a fake /proc tree, OS detection and reader selection."""

import json
from pathlib import Path

import pytest

from saber_tooth.vr import readers as real
from saber_tooth.vr.probe import Readers, probe, probe_linux


def fake_readers(comms=(), manifests=(), files=None):
    files = files or {}

    def read_text(path):
        if path not in files:
            raise FileNotFoundError(path)
        return files[path]

    return Readers(lambda: list(comms), lambda: list(manifests), read_text)


@pytest.mark.parametrize(
    ("comm", "runtime"),
    [
        ("vrserver", "SteamVR"),
        ("monado-service", "Monado"),
        ("wivrn-server", "WiVRn"),
        ("alvr_dashboard", "ALVR"),
        ("ALVR Dashboard", "ALVR"),
    ],
)
def test_each_linux_runtime_is_recognised(comm, runtime):
    assert probe_linux(fake_readers([comm, "bash"])).runtimes == [runtime]


def test_several_runtimes_are_all_reported():
    found = probe_linux(fake_readers(["monado-service", "vrserver", "vrserver"]))
    assert sorted(found.runtimes) == ["Monado", "SteamVR"]


def test_unrelated_processes_find_nothing():
    assert probe_linux(fake_readers(["bash", "Xorg", "vrserver-helper", "valvr"])).runtimes == []


def test_openxr_runtime_prefers_the_user_manifest_then_the_system_one():
    user = "/srv/u/.config/openxr/1/active_runtime.json"
    system = "/etc/xdg/openxr/1/active_runtime.json"
    files = {
        user: json.dumps({"runtime": {"name": "Monado"}}),
        system: json.dumps({"runtime": {"name": "SteamVR"}}),
    }
    assert probe_linux(fake_readers(manifests=[user, system], files=files)).xr_runtime == "Monado"
    del files[user]
    assert probe_linux(fake_readers(manifests=[user, system], files=files)).xr_runtime == "SteamVR"
    assert probe_linux(fake_readers(manifests=[user, system])).xr_runtime is None


def test_dispatch_routes_linux():
    assert probe("linux", fake_readers(["vrserver"])).runtimes == ["SteamVR"]


def test_linux_manifest_paths_are_user_then_system():
    assert real.linux_manifests("/srv/u") == [
        "/srv/u/.config/openxr/1/active_runtime.json",
        "/etc/xdg/openxr/1/active_runtime.json",
    ]


def test_linux_comms_skips_entries_that_vanish_or_cannot_be_read(tmp_path: Path):
    for pid, comm in (("1", "systemd\n"), ("42", "vrserver\n"), ("77", "wivrn-server\n")):
        (tmp_path / pid).mkdir()
        (tmp_path / pid / "comm").write_text(comm, encoding="utf-8")
    (tmp_path / "99").mkdir()  # exited between the listing and the read: no comm file
    (tmp_path / "100").mkdir()
    (tmp_path / "100" / "comm").mkdir()  # a comm that cannot be read as text
    (tmp_path / "self").mkdir()  # not a pid
    (tmp_path / "cpuinfo").write_text("x", encoding="utf-8")
    (tmp_path / "55").write_text("a file, not a directory", encoding="utf-8")
    assert sorted(real.linux_comms(tmp_path)) == ["systemd", "vrserver", "wivrn-server"]


def test_linux_comms_of_a_missing_proc_raises_and_the_probe_treats_it_as_empty(tmp_path: Path):
    missing = tmp_path / "nope"
    with pytest.raises(OSError):
        real.linux_comms(missing)
    found = probe_linux(Readers(lambda: real.linux_comms(missing), lambda: [], lambda p: ""))
    assert found.runtimes == []


@pytest.mark.parametrize(
    ("system", "expected"),
    [
        ("Windows", "windows"),
        ("Linux", "linux"),
        ("Darwin", "macos"),
        ("FreeBSD", "freebsd"),
        ("", "unknown"),
    ],
)
def test_detect_os_names(system, expected):
    assert real.detect_os(system) == expected


def test_default_readers_pick_the_real_reader_per_os():
    assert real.default_readers("windows").processes is real.windows_processes
    assert real.default_readers("windows").manifests is real.windows_manifests
    assert real.default_readers("linux").processes is real.linux_comms
    assert real.default_readers("linux").manifests is real.linux_manifests
    other = real.default_readers("macos")
    assert list(other.processes()) == [] and list(other.manifests()) == []
    assert real.default_readers("linux").read_text is real.read_text_file
```

- [ ] **Step 2: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_vr_probe_linux.py`
Expected: FAIL: `ImportError: cannot import name 'probe_linux' from 'saber_tooth.vr.probe'`.

- [ ] **Step 3: Implement**

In `src/saber_tooth/vr/probe.py`, add after `WINDOWS_PROCESSES`:

```python
LINUX_PROCESSES = {
    "vrserver": "SteamVR",
    "monado-service": "Monado",
    "wivrn-server": "WiVRn",
}
```

Add after `probe_windows`:

```python
def _linux_runtime(comm: str) -> str | None:
    name = comm.strip().lower()
    if name in LINUX_PROCESSES:
        return LINUX_PROCESSES[name]
    return "ALVR" if name.startswith("alvr") else None


def probe_linux(readers: Readers) -> Probe:
    found = {_linux_runtime(comm) for comm in _names(readers.processes)}
    return Probe(sorted(name for name in found if name), _xr(readers))
```

Replace the body of `probe`:

```python
def probe(os_name: str, readers: Readers) -> Probe:
    """The probe for `os_name` (`windows`, `linux`, `macos`); any other name finds nothing."""
    if os_name == "windows":
        return probe_windows(readers)
    if os_name == "linux":
        return probe_linux(readers)
    if os_name == "macos":
        return probe_macos(readers)
    return Probe()
```

In `src/saber_tooth/vr/readers.py`, add `import platform` to the imports, import `Readers` with `from saber_tooth.vr.probe import Readers`, and append:

```python
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
```

- [ ] **Step 4: Run it to see it pass**

Run: `rtk proxy uv run pytest -q tests/test_vr_probe_linux.py tests/test_vr_probe_windows.py`
Expected: PASS, 36 passed.

- [ ] **Step 5: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): Linux probe, OS detection and default readers" src/saber_tooth/vr tests/test_vr_probe_linux.py`
