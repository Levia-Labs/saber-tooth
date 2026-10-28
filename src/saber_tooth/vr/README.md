# vr

Headset runtime detection, standard library only. Used by `scripts/vr_agent.py` on the host and by the API's in-process mode ([api.md](../../../docs/api.md#vr-status)).

1. `model.py`: `RUNTIME_ORDER`, `Probe`, `order_runtimes`, `status_dict`, `none_status`.
2. `openxr.py`: the active OpenXR runtime's name from its manifest.
3. `probe.py`: `Readers`, one probe per OS (`probe_windows`, `probe_macos`) and `probe(os_name, readers)`.
4. `readers.py`: the real readers (`tasklist`, the OpenXR registry value, file text).

Tests: `task st:test -- tests/test_vr_model.py`.
