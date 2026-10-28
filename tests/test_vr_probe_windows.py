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
