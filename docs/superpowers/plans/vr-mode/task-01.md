# Task 1: Status model, runtime order and OpenXR names

The shared shape of the helper's answer and the fixed runtime order live in a small stdlib-only package, `src/saber_tooth/vr/`, so the host helper and the backend's in-process mode use one implementation. `scripts/vr_agent.py` (Task 5) imports it; it is run with `uv run`, which has the project installed.

**Files:**

- Create: `src/saber_tooth/vr/__init__.py`
- Create: `src/saber_tooth/vr/model.py`
- Create: `src/saber_tooth/vr/openxr.py`
- Create: `src/saber_tooth/vr/README.md`
- Test: `tests/test_vr_model.py`

**Interfaces:**

Consumes: nothing.

Produces (`vr/model.py`):

1. `RUNTIME_ORDER: tuple[str, ...]` = `("SteamVR", "Oculus", "Virtual Desktop", "Monado", "WiVRn", "ALVR")`.
2. `Probe(runtimes: list[str] = [], xr_runtime: str | None = None)`, a frozen dataclass: what one OS probe found.
3. `order_runtimes(found: Iterable[str]) -> list[str]`: known names in `RUNTIME_ORDER`, no duplicates, unknown names dropped.
4. `status_dict(os_name: str, probe: Probe, worn: bool | None) -> dict`: `{"os", "runtime", "runtimes", "xr_runtime", "worn"}`; `runtime` is the first of `runtimes`.
5. `none_status(os_name: str = "unknown") -> dict`: the same shape with no runtime and `worn` null.

Produces (`vr/openxr.py`):

1. `xr_name(path: str, text: str) -> str | None`: `runtime.name` from the manifest JSON in `text`, else the manifest's file name; None when `path` is blank.
2. `first_xr_name(paths: Iterable[str], read_text: Callable[[str], str]) -> str | None`: the name for the first path whose file reads; unreadable paths are skipped.

- [ ] **Step 1: Write the failing test**

Create `tests/test_vr_model.py`:

```python
"""The status shape, the runtime order and OpenXR manifest names."""

import json

from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.vr.model import (
    RUNTIME_ORDER,
    Probe,
    none_status,
    order_runtimes,
    status_dict,
)
from saber_tooth.vr.openxr import first_xr_name, xr_name


def test_runtime_order_is_the_spec_order():
    assert RUNTIME_ORDER == ("SteamVR", "Oculus", "Virtual Desktop", "Monado", "WiVRn", "ALVR")


def test_runtime_is_the_first_of_runtimes_in_spec_order():
    probe = Probe(["ALVR", "Oculus", "SteamVR", "Oculus"], "SteamVR OpenXR")
    assert status_dict("windows", probe, True) == {
        "os": "windows",
        "runtime": "SteamVR",
        "runtimes": ["SteamVR", "Oculus", "ALVR"],
        "xr_runtime": "SteamVR OpenXR",
        "worn": True,
    }


def test_none_status_has_the_same_keys_and_no_runtime():
    assert none_status() == {
        "os": "unknown",
        "runtime": None,
        "runtimes": [],
        "xr_runtime": None,
        "worn": None,
    }


@given(st.lists(st.sampled_from([*RUNTIME_ORDER, "Quest Link", "", "steamvr"])))
def test_order_runtimes_is_a_deduplicated_subsequence_of_the_order(found):
    ordered = order_runtimes(found)
    assert ordered == [n for n in RUNTIME_ORDER if n in found]
    assert len(ordered) == len(set(ordered))
    assert order_runtimes(ordered) == ordered


def test_xr_name_prefers_the_manifest_name():
    text = json.dumps({"runtime": {"name": " Oculus ", "library_path": "x.dll"}})
    assert xr_name("C:\\a\\oculus_openxr_64.json", text) == "Oculus"


def test_xr_name_falls_back_to_the_file_name():
    assert xr_name("C:\\a\\steamxr_win64.json", "not json") == "steamxr_win64.json"
    assert xr_name("/etc/xdg/openxr/1/active_runtime.json", "[]") == "active_runtime.json"
    assert xr_name("/a/b.json", json.dumps({"runtime": {"name": 5}})) == "b.json"
    assert xr_name("  ", "{}") is None


def test_first_xr_name_skips_unreadable_manifests():
    files = {"/etc/b.json": json.dumps({"runtime": {"name": "Monado"}})}

    def read_text(path: str) -> str:
        if path not in files:
            raise FileNotFoundError(path)
        return files[path]

    assert first_xr_name(["/srv/u/a.json", "/etc/b.json"], read_text) == "Monado"
    assert first_xr_name(["/srv/u/a.json"], read_text) is None
    assert first_xr_name([], read_text) is None


def test_first_xr_name_skips_a_manifest_that_is_not_text():
    def read_text(path: str) -> str:
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")

    assert first_xr_name(["/a.json"], read_text) is None
```

- [ ] **Step 2: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_vr_model.py`
Expected: FAIL: `ModuleNotFoundError: No module named 'saber_tooth.vr'`.

- [ ] **Step 3: Implement**

Create `src/saber_tooth/vr/__init__.py`:

```python
"""VR headset runtime detection: standard library only, shared by the host helper and the API."""
```

Create `src/saber_tooth/vr/model.py`:

```python
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
```

Create `src/saber_tooth/vr/openxr.py`:

```python
"""The name of the active OpenXR runtime, read from its manifest."""

import json
import re
from collections.abc import Callable, Iterable


def xr_name(path: str, text: str) -> str | None:
    """`runtime.name` from the manifest `text`, else the manifest's file name; None without a path."""
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
```

Create `src/saber_tooth/vr/README.md`:

```markdown
# vr

Headset runtime detection, standard library only. Used by `scripts/vr_agent.py` on the host and by the API's in-process mode ([api.md](../../../docs/api.md#vr-status)).

1. `model.py`: `RUNTIME_ORDER`, `Probe`, `order_runtimes`, `status_dict`, `none_status`.
2. `openxr.py`: the active OpenXR runtime's name from its manifest.

Tests: `task st:test -- tests/test_vr_model.py`.
```

- [ ] **Step 4: Run it to see it pass**

Run: `rtk proxy uv run pytest -q tests/test_vr_model.py`
Expected: PASS, 8 passed.

- [ ] **Step 5: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): status model, runtime order and OpenXR manifest names" src/saber_tooth/vr tests/test_vr_model.py`
