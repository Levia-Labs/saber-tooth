# Task 19: Docs (part b)

Continues [task-19a.md](task-19a.md).

- [ ] **Step 3: Write the VR page**

Create `docs/vr.md`:

```markdown
# VR mode

A layout of saber-tooth for use through a headset: large cards and buttons, 22 px text, 64 px targets, 16 px gaps and high contrast. It has three screens: the Library, a map (Fix, Delete, crop) and BeatSaver. Map review and New map stay in the desktop layout. The immersive WebXR dashboard is a later phase with its own spec.

## Opening it

The layout is chosen in this order, first match wins:

1. the address: `/vr` and everything below it, or `?mode=vr`, is VR; `?mode=desktop` is desktop and beats the `/vr` path;
2. the remembered choice, kept in the browser's local storage;
3. a standalone headset browser (Meta Quest Browser, Pico, Wolvic) is VR;
4. otherwise desktop. If the host helper reports a headset runtime, a banner asks "Headset in use: switch to VR layout?". Accept switches and remembers the choice; dismiss hides the banner for the session.

The VR / Desktop switch in the masthead, next to About, changes the layout and remembers it. Pages without a VR twin (About, New, playlists on the desktop BeatSaver page) keep their desktop content in either layout.

## Runtime detection: the host helper

The backend runs in a Linux container and cannot see host processes, so a small helper on the host reports which VR runtime is active.

1. Run `task st:vr-agent` on the host, outside Docker. It listens on `127.0.0.1:8101`; `--port N` changes the port and `--bind HOST` the address. It needs only Python and `uv`. With the optional `pyopenvr` package (`uv run --with openvr python scripts/vr_agent.py`) it also reports whether the headset is worn, read from the SteamVR activity level; without it `worn` is null.
2. `GET /status` answers `{"os", "runtime", "runtimes", "xr_runtime", "worn"}`. The runtimes are SteamVR, Oculus, Virtual Desktop, Monado, WiVRn, ALVR; `runtime` is the first of `runtimes` in that order. Windows reads the process list and the OpenXR registry value, Linux reads `/proc/*/comm` and the OpenXR manifest, macOS has no PC VR runtime and always reports none.
3. The container asks the helper at `VR_AGENT_URL` (default `http://host.docker.internal:8101/status`; `docker-compose.yml` maps `host.docker.internal` for Linux hosts). The call has a 300 ms timeout and the answer is cached for 2 s. On Linux, Docker reaches the host through the bridge gateway, not loopback: start the helper with `--bind` set to the `docker0` address (usually `172.17.0.1`) or to the host's LAN address.
4. A backend run natively, outside a container, probes in-process and needs no helper.
5. `GET /api/vr/status` adds `source`: `agent`, `local` or `none`. The page polls it every 5 s while the tab is visible and stops while it is hidden.

If the helper is not running, nothing breaks: the status is "no runtime", no banner shows and `/vr` still works. If port 8101 is taken, the helper exits with a message that names `--port` and `VR_AGENT_URL`.

## LAN access for a standalone headset

A Quest, Pico or other standalone headset reaches saber-tooth over the network. This is off by default.

1. Set `SABER_BIND=0.0.0.0` in `.env` (default `127.0.0.1`) so the compose port listens on the network.
2. Set `SABER_ALLOWED_HOSTS` to the host names the headset uses, for example `SABER_ALLOWED_HOSTS=192.168.1.50`. A request whose `Host` is not listed is refused with 403 `{"error": "host not allowed"}`.
3. Open `http://<host>:8100/vr` in the headset browser.

Warning: saber-tooth has no login, so anyone on the network can fix, crop, download and permanently delete map folders while it is on. Turn `SABER_BIND` back to `127.0.0.1` when you are done.

## Manual headset checklist

Run it for each of Oculus Dash, SteamVR Desktop and Virtual Desktop, with `task st:vr-agent` running and a few maps in the library.

1. Open `/vr` in the desktop browser the dashboard shows. The layout is large and high contrast.
2. Point the controller laser at a card and press the trigger. The Preview, Fix and Open buttons respond.
3. Scroll the list with the thumbstick. More cards load near the end.
4. Open a map and press Fix. The progress banner shows at the top at VR size; the Fixed copy appears.
5. Open Crop, switch 1 min and 2 min, press Previous section, Next section, End earlier and End later, then Create cropped map. The new folder is announced.
6. Open BeatSaver, press a preset and press Download on one map. It shows Installed afterwards.
7. With SteamVR running and `pyopenvr` installed, take the headset off and on: `worn` in `/api/vr/status` turns false and true.
8. Close the helper. The banner does not return after you dismissed it, `/vr` keeps working and the status shows no runtime.
```

- [ ] **Step 4: Write the other doc edits**

In `docs/api.md`, add this line before the `1. \`GET /api/maps/{id}/timeline\``item in`## Routes`:

```markdown
1. `GET /api/vr/status`: the headset runtime status with its `source`; see [VR status](#vr-status).
```

and add this section before `## URL rule`:

```markdown
## VR status

1. `GET /api/vr/status` answers `{"os": str, "runtime": str | null, "runtimes": [str], "xr_runtime": str | null, "worn": bool | null, "source": "agent" | "local" | "none"}`. `runtime` is the first of `runtimes` in the order SteamVR, Oculus, Virtual Desktop, Monado, WiVRn, ALVR.
2. In a container the service asks the host helper at `VR_AGENT_URL` (default `http://host.docker.internal:8101/status`, started with `task st:vr-agent`); run natively it probes in-process. The call has a 300 ms timeout and the answer is cached for 2 s. Any failure still answers 200 with `runtime: null`, `runtimes: []`, `worn: null` and `source: "none"`.
3. The route is not an MCP tool. `GET /vr`, `GET /vr/maps/{id}` and `GET /vr/beatsaver` answer with `index.html` like the other pages. See [VR mode](vr.md).
```

In `docs/README.md`, add after item 8:

```markdown
9. [vr.md](vr.md): VR mode: opening it, the host helper, LAN access with its warning and the manual headset checklist.
```

In `README.md`, add after the `task st:docker-health` row:

```markdown
| `task st:vr-agent` | Run the VR runtime helper on the host (port 8101) |
```

In `scripts/README.md`, add after item 13:

```markdown
14. `vr_agent.py`: the host helper that reports the active VR runtime on `127.0.0.1:8101` for the backend's `/api/vr/status`; standard library only, optional `pyopenvr` for the worn check. `task st:vr-agent [-- --port N --bind HOST]`. Tested by `tests/test_script_vr_agent.py`.
```

and change item 11 from "opens the Library, a map, BeatSaver, playlists and About" to "opens the Library, a map, BeatSaver, playlists, About and the three VR screens".

In `tests/README.md`, change `` `test_api_crop`. `` to `` `test_api_crop`, `test_vr_*` (probes, worn check, status client), `test_api_vr`, `test_compose_vr`, `test_script_vr_agent`, `test_docs_vr`. ``.

In `frontend/tests/README.md`, add one item after the last list item (keep the numbering going): `` `vr*.test.ts(x)`: the VR layout: status poll, mode decision, provider, shell switch and banner, `vr.css` sizes, the Library, Map and BeatSaver screens, crop steps and routes. ``

Replace the body of `src/saber_tooth/vr/README.md` with:

```markdown
# vr

Headset runtime detection, standard library only. Used by `scripts/vr_agent.py` on the host and by the API's in-process mode ([api.md](../../../docs/api.md#vr-status), [vr.md](../../../docs/vr.md)).

1. `model.py`: `RUNTIME_ORDER`, `Probe`, `order_runtimes`, `status_dict`, `none_status`.
2. `openxr.py`: the active OpenXR runtime's name from its manifest.
3. `probe.py`: `Readers`, one probe per OS (`probe_windows`, `probe_linux`, `probe_macos`) and `probe(os_name, readers)`.
4. `readers.py`: the real readers (`tasklist`, the OpenXR registry value, `/proc/*/comm`, file text), `detect_os`, `default_readers`.
5. `worn.py`: `WornMonitor`, the optional pyopenvr worn check (background OpenVR connection, one log line per failure kind).

Tests: `task st:test -- tests/test_vr_model.py tests/test_vr_probe_windows.py tests/test_vr_probe_linux.py tests/test_vr_worn.py`.
```

Replace the body of `frontend/src/vr/README.md` with:

```markdown
# vr

The VR layout: mode decision, headset status, screens and the CSS hooks they use. See [the VR mode design](../../../docs/superpowers/specs/2026-10-28-vr-mode-design.md) and [vr.md](../../../docs/vr.md).

1. `status.ts`: `GET /api/vr/status` client, query options and the 5 s visibility-aware poll.
2. `mode.ts`: the pure mode decision (address, remembered choice, headset browser, default), storage helpers, `/vr` path mapping and the WebXR probe.
3. `VrMode.tsx`: `VrModeProvider` and `useVrMode`: the decided mode, headset status, banner state, `choose`, the `data-ui` attribute and the redirects between desktop and VR paths.
4. `presets.ts`, `VrNav.tsx`, `useNearEnd.ts`, `VrCard.tsx`, `VrLibraryPage.tsx`: the `/vr` Library screen.
5. `CropSteps.tsx`, `VrMapPage.tsx`: the `/vr/maps/:id` screen; `CropPanel` takes `steps` to show the four large step buttons.
6. `VrBsCard.tsx`, `VrBsPlaylists.tsx`, `VrBeatSaverPage.tsx`: the `/vr/beatsaver` screen.
7. `VrBanner.tsx`, `ModeSwitch.tsx`: the suggestion banner and the masthead VR / Desktop switch, mounted by `Shell` inside `VrModeProvider`.

Routes are lazy routes in `App.tsx`; the server answers `/vr`, `/vr/maps/{id}` and `/vr/beatsaver` with `index.html` on reload. Styles: `styles/vr.css` (active only under `[data-ui="vr"]`) and `styles/vrmode.css` (switch and banner).
```

- [ ] **Step 5: Run the test to see it pass**

Run: `rtk proxy uv run pytest -q tests/test_docs_vr.py tests/test_readme_check.py`
Expected: PASS, 9 passed in `test_docs_vr.py`.

- [ ] **Step 6: Check the folder READMEs and the compose file**

Run: `rtk proxy task st:readme-check`
Expected: exit 0. Then `rtk proxy task st:compose-check` (Task 8) and, because `docker-compose.yml` changed in this plan, the container e2e gate: `task st:release` (dry run), then `task st:up` and `task st:smoke` and `task st:browser-check`. Say in the receipt which of these ran.

- [ ] **Step 7: Commit**

Commit: main thread runs `task st:commit -- -m "docs(vr): VR mode page, API section, task and README rows, headset checklist and LAN warning" docs/vr.md docs/api.md docs/README.md README.md scripts/README.md tests/README.md frontend/tests/README.md src/saber_tooth/vr/README.md frontend/src/vr/README.md tests/test_docs_vr.py`
