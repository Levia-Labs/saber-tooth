# docs/superpowers/plans

1. [`v1/`](v1/index.md): the step-by-step implementation plan for v1, one file per task.
2. [`crop-highlight/`](crop-highlight/index.md): crop a map to a 1 or 2 minute highlight: the `crop` package, timeline and crop job, MCP tools and the map page panel (18 tasks). Spec: [crop highlight design](../specs/2026-10-28-crop-highlight-design.md).
3. [`vr-mode/`](vr-mode/index.md): use saber-tooth from a VR headset: the host runtime helper, `GET /api/vr/status`, the mode decision, the `/vr` layout and its three screens (19 tasks). Spec: [VR mode design](../specs/2026-10-28-vr-mode-design.md).
4. [`jobs-queue/`](jobs-queue/index.md): a durable job queue drained by one worker, `GET /api/jobs` and cancel, the Jobs tab, and job toasts that survive a refresh (8 tasks). Spec: [jobs queue design](../specs/2026-10-29-jobs-queue-design.md).

The plan is a historical record of the build order. Current structure is in [architecture](../../architecture.md). Design: [specs](../specs/README.md).
