"""The VR docs carry the spec's mandatory facts and follow the repo rules."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WARNING = (
    "saber-tooth has no login, so anyone on the network can fix, crop, download and "
    "permanently delete map folders while it is on."
)
EM_DASH = chr(0x2014)
VR_DOCS = (
    "docs/vr.md",
    "src/saber_tooth/vr/README.md",
    "frontend/src/vr/README.md",
    "docs/superpowers/specs/2026-10-28-vr-mode-design.md",
)


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
        "extra_hosts",
        "405",
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
    for needle in (
        "?mode=vr",
        "?mode=desktop",
        "/vr",
        "Meta Quest Browser",
        "Pico",
        "Wolvic",
        "case-insensitive",
        "Headset in use",
        "Not now",
    ):
        assert needle in page
    assert (
        page.index("the address") < page.index("remembered choice") < page.index("headset browser")
    )


def test_the_manual_checklist_covers_the_three_dashboards():
    page = read("docs/vr.md")
    for needle in ("Oculus Dash", "SteamVR Desktop", "Virtual Desktop", "laser", "thumbstick"):
        assert needle in page
    checklist = page.split("## Manual headset checklist")[1]
    for step in ("Fix", "crop", "BeatSaver", "Previous section", "End 1 s later"):
        assert step in checklist


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


def test_the_spec_amendment_records_the_shipped_changes():
    spec = read("docs/superpowers/specs/2026-10-28-vr-mode-design.md")
    amendments = spec.split("## Amendments")[1]
    for needle in ("toast", "Not now", "free cutting", "case-insensitive", "403"):
        assert needle in amendments


def test_the_vr_docs_have_no_em_dash_and_stay_within_300_lines():
    for rel in VR_DOCS:
        text = read(rel)
        assert EM_DASH not in text, rel
        assert len(text.splitlines()) <= 300, rel
        assert "\r" not in text, rel
