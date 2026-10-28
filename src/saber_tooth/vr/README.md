# vr

Headset runtime detection, standard library only. Used by `scripts/vr_agent.py` on the host and by the API's in-process mode ([api.md](../../../docs/api.md#vr-status), [vr.md](../../../docs/vr.md)).

1. `model.py`: `RUNTIME_ORDER`, `Probe`, `order_runtimes`, `status_dict`, `none_status`.
2. `openxr.py`: the active OpenXR runtime's name from its manifest.
3. `probe.py`: `Readers`, one probe per OS (`probe_windows`, `probe_linux`, `probe_macos`) and `probe(os_name, readers)`.
4. `readers.py`: the real readers (`tasklist`, `/proc/*/comm`, the OpenXR registry value and manifest paths, file text), `detect_os` and `default_readers`.
5. `worn.py`: `WornMonitor`, the optional pyopenvr worn check (background OpenVR connection, one log line per failure kind).

Tests: `task st:test -- tests/test_vr_model.py tests/test_vr_probe_windows.py tests/test_vr_probe_linux.py tests/test_vr_worn.py tests/test_vr_status.py`.
