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
