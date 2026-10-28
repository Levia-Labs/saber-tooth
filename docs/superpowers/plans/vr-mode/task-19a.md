# Task 19: Docs: VR page, API section, README rows, headset checklist, LAN warning

One new page, `docs/vr.md`, holds the setup, the helper, the LAN warning and the manual headset checklist; `docs/api.md` gets the route; the root README and the folder READMEs list the new task, scripts, folders and tests. The doc test pins the strings the spec makes mandatory (the warning text, the port and timeout values, the three dashboards) so they cannot drift. The LAN section states today's behaviour: an unlisted host is refused with 403 `{"error": "host not allowed"}` by the existing host check, not the 400 the spec text names.

**Files:**

- Create: `docs/vr.md`
- Modify: `docs/api.md` (one list item, one section)
- Modify: `docs/README.md` (one list item)
- Modify: `README.md` (one table row)
- Modify: `scripts/README.md` (one list item, one clause)
- Modify: `tests/README.md`, `frontend/tests/README.md` (one item each)
- Modify: `src/saber_tooth/vr/README.md`, `frontend/src/vr/README.md` (finish the lists)
- Test: `tests/test_docs_vr.py`

**Interfaces:**

Consumes: every name defined in Tasks 1 to 18.

Produces: the pages above; no code.

- [ ] **Step 1: Write the failing test**

Create `tests/test_docs_vr.py`:

```python
"""The VR docs carry the spec's mandatory facts and the plan files follow the repo rules."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WARNING = (
    "saber-tooth has no login, so anyone on the network can fix, crop, download and "
    "permanently delete map folders while it is on."
)
EM_DASH = chr(0x2014)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_the_lan_warning_is_verbatim_and_names_the_settings():
    page = read("docs/vr.md")
    assert WARNING in page
    for needle in ("SABER_BIND=0.0.0.0", "SABER_ALLOWED_HOSTS", "127.0.0.1", "403"):
        assert needle in page


def test_the_helper_facts_are_documented():
    page = read("docs/vr.md")
    for needle in (
        "task st:vr-agent",
        "8101",
        "--port",
        "--bind",
        "VR_AGENT_URL",
        "host.docker.internal",
        "300 ms",
        "2 s",
        "5 s",
        "pyopenvr",
    ):
        assert needle in page


def test_the_runtime_order_is_documented_in_the_spec_order():
    page = read("docs/vr.md")
    order = ["SteamVR", "Oculus", "Virtual Desktop", "Monado", "WiVRn", "ALVR"]
    line = next(ln for ln in page.splitlines() if "SteamVR, Oculus" in ln)
    positions = [line.index(name) for name in order]
    assert positions == sorted(positions)


def test_the_mode_decision_order_is_documented():
    page = read("docs/vr.md")
    for needle in ("?mode=vr", "?mode=desktop", "/vr", "Meta Quest Browser", "Pico", "Wolvic"):
        assert needle in page
    assert (
        page.index("the address") < page.index("remembered choice") < page.index("headset browser")
    )


def test_the_manual_checklist_covers_the_three_dashboards():
    page = read("docs/vr.md")
    for needle in ("Oculus Dash", "SteamVR Desktop", "Virtual Desktop", "laser", "thumbstick"):
        assert needle in page
    for step in ("Fix", "crop", "BeatSaver"):
        assert step in page.split("## Manual headset checklist")[1]


def test_the_route_and_task_are_listed():
    assert "/api/vr/status" in read("docs/api.md")
    assert "## VR status" in read("docs/api.md")
    assert "st:vr-agent" in read("README.md")
    assert "vr_agent.py" in read("scripts/README.md")
    assert "vr.md" in read("docs/README.md")


def test_the_new_folders_have_a_readme_listing_their_modules():
    py = read("src/saber_tooth/vr/README.md")
    for name in ("model.py", "openxr.py", "probe.py", "readers.py", "worn.py"):
        assert name in py
    ts = read("frontend/src/vr/README.md")
    for name in ("status.ts", "mode.ts", "VrMode.tsx", "VrLibraryPage.tsx", "VrMapPage.tsx"):
        assert name in ts
    assert "VrBeatSaverPage.tsx" in ts and "ModeSwitch.tsx" in ts


def test_the_plan_files_have_no_em_dash_and_stay_within_300_lines():
    folder = ROOT / "docs" / "superpowers" / "plans" / "vr-mode"
    for path in sorted(folder.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert EM_DASH not in text, path.name
        assert len(text.splitlines()) <= 300, path.name
        assert "\r" not in text, path.name


def test_the_vr_docs_have_no_em_dash():
    for rel in ("docs/vr.md", "src/saber_tooth/vr/README.md", "frontend/src/vr/README.md"):
        assert EM_DASH not in read(rel), rel
```

- [ ] **Step 2: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_docs_vr.py`
Expected: FAIL: `FileNotFoundError` for `docs/vr.md`.

Continued in [task-19b.md](task-19b.md).
