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
