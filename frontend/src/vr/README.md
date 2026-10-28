# vr

The VR layout: mode decision, headset status, screens and the CSS hooks they use. See [the VR mode design](../../../docs/superpowers/specs/2026-10-28-vr-mode-design.md).

1. `status.ts`: `GET /api/vr/status` client, query options and the 5 s visibility-aware poll.
2. `mode.ts`: the pure mode decision (URL, remembered choice, headset browser, default), storage helpers, `/vr` path mapping and the WebXR probe.
