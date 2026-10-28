# vr

Headset runtime detection, standard library only. Used by `scripts/vr_agent.py` on the host and by the API's in-process mode ([api.md](../../../docs/api.md#vr-status)).

1. `model.py`: `RUNTIME_ORDER`, `Probe`, `order_runtimes`, `status_dict`, `none_status`.
2. `openxr.py`: the active OpenXR runtime's name from its manifest.

Tests: `task st:test -- tests/test_vr_model.py`.
