# VR Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use saber-tooth from inside a VR headset: a 2D layout built for viewing through the headset (Library, Crop and BeatSaver flows), switched on by URL, by a remembered choice, or by a suggestion when a VR runtime is active, with detection of the headset runtime on Windows, Linux and macOS.

**Architecture:** A stdlib-only package `src/saber_tooth/vr/` (status model, one probe per OS behind injected readers, optional OpenVR worn check) is used by a host helper `scripts/vr_agent.py` (`task st:vr-agent`, `GET /status` on `127.0.0.1:8101`) and by the backend. A `VrStatusClient` and `vr_routes.py`, built like `crop_routes.py`, serve `GET /api/vr/status` (helper over HTTP in a container, in-process when native). `docker-compose.yml` gains `extra_hosts` and `SABER_BIND`. The React app gains `frontend/src/vr/`: a status poll, a pure mode decision, a `VrMode` context (redirects, `data-ui="vr"`), a banner and masthead switch in `Shell`, `vr.css`, and three lazy screens (`/vr`, `/vr/maps/:id`, `/vr/beatsaver`). The map screen reuses the crop panel and NPS chart of the crop-highlight plan through a new `steps` prop.

**Tech Stack:** Python 3.12, uv, FastAPI, httpx, pytest, hypothesis, ruff; React 19, TypeScript, TanStack Query, react-router, vitest, Testing Library, fast-check.

**Spec:** `docs/superpowers/specs/2026-10-28-vr-mode-design.md`

## Global Constraints

Values copied from the spec; tests pin them, code must not change them.

1. Helper: `scripts/vr_agent.py` serves `GET /status` on `127.0.0.1:8101` (port set by `--port`), JSON `{"os": str, "runtime": str | null, "runtimes": [str], "xr_runtime": str | null, "worn": bool | null}`. Standard library only; the worn check uses the optional `pyopenvr` package.
2. Backend `GET /api/vr/status`: timeout 300 ms, answer cached 2 s, `VR_AGENT_URL` default `http://host.docker.internal:8101/status`; on any failure the same shape with `runtime: null`, `runtimes: []`, `worn: null` and `source: "none"`, otherwise `source` is `"agent"` or `"local"`; run natively it calls the probe in-process. Not exposed as an MCP tool.
3. Frontend poll: `/api/vr/status` every 5 s while the tab is visible, stopped while hidden. `navigator.xr.isSessionSupported('immersive-vr')` is read once; a missing or blocked API is unsupported with no console error.
4. Mode decision order: the URL (`/vr...` or `?mode=vr` is VR, `?mode=desktop` is desktop), then the remembered choice (local storage inside try/catch), then a standalone headset browser user agent (VR), otherwise desktop with the banner "Headset in use: switch to VR layout?" when the status reports a runtime (accept switches and remembers, dismiss hides it for the session). `data-ui="vr"` on the root element in VR mode; the VR / Desktop switch sits in the masthead next to About.
5. Runtime order: SteamVR, Oculus, Virtual Desktop, Monado, WiVRn, ALVR; `runtime` is the first of `runtimes` in that order. Worn: user interaction means worn, idle or standby means not worn, otherwise `null`.
6. Layout: text 22 px, interactive targets at least 64 px, gaps 16 px, high-contrast tokens, an always-visible focus ring, no hover-only tooltips (help shows as text under the control), a grid of 1 to 3 columns by container width; job banners at VR size near the top.
7. LAN: `SABER_BIND` default `127.0.0.1`, `0.0.0.0` makes the compose port listen on the network, `SABER_ALLOWED_HOSTS` must list the host names; `docker-compose.yml` has `extra_hosts: ["host.docker.internal:host-gateway"]`. Security warning text: "saber-tooth has no login, so anyone on the network can fix, crop, download and permanently delete map folders while it is on."
8. Scope: Library, Crop and BeatSaver screens only; map review, New map, free-text search, the immersive WebXR dashboard and LAN authentication are non-goals.
9. Repo rules: Python 3.12 and uv; every file at most 300 lines; `encoding="utf-8"` on every text read and write; numbered lists in docs; no em dashes anywhere; tests never touch real processes, the registry, SteamVR or user data (fake readers, a fake OpenVR module and a loopback fake helper only); a new directory needs a README; shared files (`api/__init__.py`, `web_routes.py`, `App.tsx`, `main.tsx`, `CropPanel.tsx`, `tests/setup.ts`, the READMEs, `docs/api.md`) get anchored `Edit` calls that add lines.

## Review Focus

Input classes the spec implies but no requirement names, most likely first. Each is pinned by a named test in the task that owns it.

1. Lookalike VR paths and odd `mode` values (`/vrx`, `/vr-maps`, `?mode=vr2`, `?mode=VR`, an empty value): the path match must be exact and the query value must be known. Pinned by `a lookalike path or an unknown mode value does not force a mode` and `any word glued to /vr is not the VR path` (Task 10).
2. Blocked or garbage browser storage (private windows, a denied `localStorage` getter, a stored value that is neither `vr` nor `desktop`): the mode must still be decided and nothing may throw. Pinned by `storage that throws on read and write still decides a mode`, `a storage object that cannot be reached at all is treated as empty` and `round trips and treats garbage as nothing` (Task 10).
3. Helper answers that are not the documented shape (wrong types, a huge body, non-JSON, HTTP errors, a slow answer): all count as the helper being down, and the failure is cached for 2 s. Pinned by `test_malformed_agent_answers_count_as_down`, `test_a_slow_helper_is_given_up_on_after_the_timeout`, `test_a_failed_probe_is_cached_for_two_seconds_too` and the property `test_clean_status_never_raises_and_only_returns_the_documented_shape` (Task 6), with `treats %j as no headset` (Task 9) on the browser side.
4. Process list quirks (image names in other case or with padding, a pid that exits between the listing and the read, an unreadable `comm`, non-text entries, a reader that raises): the probe skips the bad entry and the other sources still run. Pinned by `test_windows_process_names_match_case_insensitively_and_ignore_padding`, `test_non_text_process_entries_are_ignored` (Task 2) and `test_linux_comms_skips_entries_that_vanish_or_cannot_be_read` (Task 3).
5. Crop step buttons at the edges (Previous section on the first start, End later on the last allowed end, End earlier on the first): the window must stay put, not wrap or throw. Pinned by `step buttons stay put at the first and last allowed point` (Task 14).

## Findings Against the Spec

1. The spec says an unlisted LAN host "answers 400". The existing host check answers 403 `{"error": "host not allowed"}` (`src/saber_tooth/api/__init__.py:86`). Tasks 7 and 19 pin and document 403; the code is not changed.
2. The helper is specified as `scripts/vr_agent.py` with the probe called "in-process" by the backend, but `scripts/` is not importable from `src/saber_tooth`. The probes live in `src/saber_tooth/vr/` (stdlib only) and the script imports them; run it with `uv run`, which has the project installed.
3. `--bind` is added to the helper (default `127.0.0.1`). On Linux, Docker's `host-gateway` is the bridge address, which a loopback-only helper does not answer; `docs/vr.md` says when to use it.
4. The library API has no filter for fixed copies (`LibraryState` in `frontend/src/lib/urlstate.ts` and the query parser in `src/saber_tooth/api/library.py` have none), so that preset filters the loaded cards in the browser by `original_id` (Task 13).
5. "Missing levels" maps to `status=incomplete`: never scanned and lacking a level (`src/saber_tooth/store_maps.py:81`) (Task 13).
6. Task 14 edits `CropPanel.tsx`, which the crop-highlight lane is still building; run it after that lane merges.

---

## Tasks

1. [Task 1: Status model, runtime order and OpenXR names](task-01.md)
1. [Task 2: Windows and macOS probes with injected readers](task-02.md)
1. [Task 3: Linux probe, OS detection and the default readers](task-03.md)
1. [Task 4: Worn check through OpenVR](task-04.md)
1. [Task 5: Host helper `scripts/vr_agent.py` and `task st:vr-agent`](task-05a.md)
1. [Task 5: Host helper `scripts/vr_agent.py` and `task st:vr-agent`](task-05b.md)
1. [Task 6: Backend status client](task-06a.md)
1. [Task 6: Backend status client](task-06b.md)
1. [Task 7: `GET /api/vr/status` route, SPA routes and the LAN host check](task-07.md)
1. [Task 8: Compose: `extra_hosts`, `SABER_BIND` and `VR_AGENT_URL`](task-08.md)
1. [Task 9: Frontend status client and query](task-09.md)
1. [Task 10: Mode decision, storage, path mapping and WebXR probe](task-10a.md)
1. [Task 10: Mode decision, storage, path mapping and WebXR probe](task-10b.md)
1. [Task 11: `VrMode` context, redirects and the `data-ui` attribute](task-11a.md)
1. [Task 11: `VrMode` context, redirects and the `data-ui` attribute](task-11b.md)
1. [Task 12: `vr.css` base layer and its size test](task-12a.md)
1. [Task 12: `vr.css` base layer and its size test](task-12b.md)
1. [Task 13: VR Library screen](task-13a.md)
1. [Task 13: VR Library screen](task-13b.md)
1. [Task 13: VR Library screen](task-13c.md)
1. [Task 13: VR Library screen](task-13d.md)
1. [Task 14: VR Map screen](task-14a.md)
1. [Task 14: VR Map screen](task-14b.md)
1. [Task 14: VR Map screen](task-14c.md)
1. [Task 15: VR BeatSaver screen](task-15a.md)
1. [Task 15: VR BeatSaver screen](task-15b.md)
1. [Task 15: VR BeatSaver screen](task-15c.md)
1. [Task 16: Router wiring for the three VR screens](task-16.md)
1. [Task 17: Shell wiring: provider, banner and the masthead switch](task-17a.md)
1. [Task 17: Shell wiring: provider, banner and the masthead switch](task-17b.md)
1. [Task 18: Browser-check and smoke routes](task-18.md)
1. [Task 19: Docs](task-19a.md)
1. [Task 19: Docs](task-19b.md)

## Spec Coverage

1. User requirements 1 to 3: the VR screens are the Library (Task 13), the map with Fix, Delete and Crop (Task 14) and BeatSaver (Task 15); review and New map are untouched.
2. Requirement 4: WebXR read (Tasks 10, 11), the backend endpoint (Tasks 6, 7), the helper (Tasks 1 to 5).
3. Requirement 5: `/vr` and `?mode=vr` (Tasks 10, 11, 16).
4. Requirement 6: sizes, contrast, focus, no tooltips, 1 to 3 columns (Task 12); presets and steppers instead of typing (Tasks 13 to 15); mouse, keyboard and laser all use ordinary buttons and links.
5. Requirement 7: Windows, Linux, macOS probes (Tasks 2, 3).
6. Architecture: helper (Tasks 1 to 5), backend (Tasks 6, 7), compose and LAN (Task 8), mode and banner and switch (Tasks 10, 11, 17), layout and screens (Tasks 12 to 16).
7. Error handling 1 to 7: helper down, slow, `pyopenvr` missing, port taken, unreadable process list, WebXR blocked, unlisted host (Tasks 4 to 7, 10, 11, 19).
8. Testing: helper tests (Tasks 1 to 5), backend tests (Tasks 6 to 8), frontend tests (Tasks 9 to 11, 17), screen tests and the `vr.css` size check (Tasks 12 to 16), browser-check routes (Task 18), manual headset checklist (Task 19).
