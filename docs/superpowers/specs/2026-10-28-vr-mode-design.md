# VR mode design

Date: 2026-10-28. Status: design approved in conversation; written spec pending review.

## Goal

Use saber-tooth from inside a VR headset: a 2D layout built for viewing through the headset, switched on by URL,
by a remembered choice, or by a suggestion when a VR runtime is active. A fully immersive WebXR dashboard is a
later phase with its own spec.

## User requirements

1. The headset is an Oculus Rift on a Windows PC. The desktop is viewed in the headset through Oculus Dash, the
   SteamVR dashboard or Virtual Desktop, depending on the session.
2. Use happens both while Beat Saber is running (pause, open the desktop view, fix or crop, return) and between games.
3. Inside VR the user needs the Library, Crop and BeatSaver flows. Map review and New map stay desktop-only.
4. Detect VR: WebXR in the browser, plus a backend endpoint that reports the headset runtime status.
5. `/vr` and `?mode=vr` open the VR layout.
6. The layout favours large buttons, readable type, high contrast, generous spacing, minimal text entry (toggles,
   presets, lists), works at any virtual desktop size, and works with mouse, keyboard and VR controllers.
7. Detection works on Windows, Linux and macOS.

## Facts that shape the design

1. A browser shown through Dash, SteamVR Desktop or Virtual Desktop is the normal desktop browser. The page cannot
   tell whether the user looks at it through a headset.
2. `navigator.xr.isSessionSupported('immersive-vr')` is true whenever a runtime is installed, worn or not.
3. The backend runs in a Linux container and cannot see host processes; a host-side helper reports runtime state.
4. Whether the headset is worn is readable only through SteamVR (OpenVR activity level of the HMD) while SteamVR runs.
5. In the dashboards the controller laser acts as a mouse pointer and the thumbstick scrolls.
6. An immersive WebXR session takes over the headset and cannot overlay a running game.
7. A standalone headset browser (Meta Quest Browser, Pico, Wolvic) is detectable from its user agent.

## Architecture

### Host helper (`scripts/vr_agent.py`, `task st:vr-agent`)

1. Runs on the host, outside Docker, standard library only; the worn check uses the optional `pyopenvr` package.
2. Serves `GET /status` on `127.0.0.1:8101` (port set by `--port`), JSON:
   `{"os": str, "runtime": str | null, "runtimes": [str], "xr_runtime": str | null, "worn": bool | null}`.
3. One probe per OS behind a common function; each probe takes injected readers so tests pass fake data.
   1. Windows: process list (`OVRServer_x64.exe` Oculus, `vrserver.exe` and `vrcompositor.exe` SteamVR,
      `VirtualDesktop.Streamer.exe` Virtual Desktop); OpenXR runtime from
      `HKLM\SOFTWARE\Khronos\OpenXR\1\ActiveRuntime`.
   2. Linux: `/proc/*/comm` (`vrserver` SteamVR, `monado-service` Monado, `wivrn-server` WiVRn, ALVR); OpenXR
      runtime from `~/.config/openxr/1/active_runtime.json`, else `/etc/xdg/openxr/1/active_runtime.json`.
   3. macOS: no PC VR runtime exists; `runtime` is always null.
   4. Worn: with SteamVR running and `pyopenvr` installed, a background OpenVR connection reads the HMD activity
      level; user interaction means worn, idle or standby means not worn; otherwise `worn` is null.
4. `runtime` is the first of `runtimes` in the order SteamVR, Oculus, Virtual Desktop, Monado, WiVRn, ALVR.

### Backend (`GET /api/vr/status`)

1. In the container it calls the helper at `VR_AGENT_URL`, default `http://host.docker.internal:8101/status`.
2. `docker-compose.yml` adds `extra_hosts: ["host.docker.internal:host-gateway"]` for Linux hosts.
3. Run natively (not in a container), it calls the probe in-process.
4. Timeout 300 ms; the answer is cached for 2 s; on any failure it returns the same shape with `runtime: null`,
   `runtimes: []`, `worn: null` and `source: "none"`; otherwise `source` is `"agent"` or `"local"`.
5. Not exposed as an MCP tool.

### Optional LAN access for standalone headsets

1. `SABER_BIND=0.0.0.0` (default `127.0.0.1`) makes the compose port listen on the network; `SABER_ALLOWED_HOSTS`
   must list the host names used.
2. Off by default. The docs carry a security warning: saber-tooth has no login, so anyone on the network can fix,
   crop, download and permanently delete map folders while it is on.

### Frontend mode

1. `VrMode` context decides the mode, in this order:
   1. URL: `/vr...` or `?mode=vr` gives VR; `?mode=desktop` gives desktop;
   2. the remembered choice (local storage, read and written inside try/catch);
   3. a standalone headset browser user agent gives VR;
   4. otherwise desktop, with a banner "Headset in use: switch to VR layout?" when `/api/vr/status` reports a
      runtime (accept switches and remembers; dismiss hides it for the session).
2. Polls `/api/vr/status` every 5 s while the tab is visible; stops while hidden.
3. Reads `navigator.xr.isSessionSupported('immersive-vr')` once for the later immersive phase; a missing or blocked
   API counts as unsupported without console errors.
4. Sets `data-ui="vr"` on the root element in VR mode; a VR / Desktop switch sits in the masthead next to About.

### VR layout

1. `vr.css`, active only under `[data-ui="vr"]`: base text 22 px, interactive targets at least 64 px, 16 px gaps,
   high-contrast tokens, always-visible focus ring, no hover-only tooltips (help shows as text under the control),
   grid of 1 to 3 columns by container width.
2. Screens, reusing the existing API client and queries:
   1. `/vr` Library: large cards (cover, title, status chip, levels, length) with Preview, Fix and Open (or Open fixed
      copy); preset toggles above (Needs fix, Missing levels, Not scanned, Fixed copies, Expert+) and a sort choice;
      no text search; more cards load on scroll.
   2. `/vr/maps/:id` Map: header, status, banners, large Fix, Delete with confirm, and the Crop panel with the 1 min /
      2 min switch, the NPS chart, and step buttons (start: previous / next section; end: minus / plus one allowed end
      point), Reset to suggestion and Create cropped map; no drag needed.
   3. `/vr/beatsaver` BeatSaver: existing presets, sort and paging, playlists, large Download per card; no free-text
      search.
3. Job banners show at VR size near the top.

## Error handling

1. Helper not running: `runtime: null`, no banner, `/vr` still works.
2. Helper slow or crashing: 300 ms timeout, treated as not running; at most one log line per minute.
3. `pyopenvr` missing or SteamVR closed: `worn: null`; runtime detection still works; the helper logs once.
4. Port 8101 taken: the helper exits with a clear message naming `--port` and `VR_AGENT_URL`.
5. Unknown OS or unreadable process list: that probe returns empty results; the others still run.
6. WebXR missing or blocked: treated as unsupported, no console errors.
7. LAN access on with an unlisted host: the existing host check answers 400; the docs show the needed setting.

## Testing

1. Helper (pytest; no real processes, registry or SteamVR): each OS probe with fake process lists and fake OpenXR
   files or registry readers; worn, idle and missing with a fake OpenVR module; the `/status` JSON shape; port conflict.
2. Backend (pytest): proxy through a fake HTTP helper (up, down, slow); the 2 s cache; in-process mode; compose has
   `extra_hosts`.
3. Frontend (vitest): mode decision order; user agents of Quest, Pico, Wolvic and ordinary desktop browsers; polling
   pauses while hidden; banner accept and dismiss; masthead switch.
4. VR screens (vitest): Library presets build the right queries and cards carry their actions; Crop step buttons move
   to the next and previous allowed point; BeatSaver presets and Download; a check that `vr.css` sets targets of at
   least 64 px and text of at least 22 px.
5. `st:browser-check` also loads `/vr`, `/vr/maps/:id` and `/vr/beatsaver` with zero console errors.
6. Manual headset checklist in the docs for Oculus Dash, SteamVR Desktop and Virtual Desktop: open `/vr`, select with
   the laser, scroll with the thumbstick, run Fix, step a crop window, download from BeatSaver.

## Non-goals

1. The immersive WebXR dashboard (React Three Fiber, `@react-three/xr`, head-following panel, controller input):
   later phase, own spec. It can only run between games.
2. Map review and New map in the VR layout.
3. Free-text search in the VR layout.
4. Authentication for LAN access.
