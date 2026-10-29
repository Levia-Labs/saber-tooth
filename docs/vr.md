# VR mode

A layout of saber-tooth for use through a headset: the desktop pages scaled up with the window (about 2x on a 1920 px wide window, 1.5x at 1280, never below the desktop size: a root font size of 8 px + 1.25vw, between 16 and 48 px) in one centered column with high contrast. The table switches columns at the width the desktop would have after the same zoom (the window width over the scale), so a 1440 px window gets the layout the desktop shows at about 900 px. The functions and layout are the desktop ones: the Library table (`/vr`), the map page (`/vr/maps/:id`), BeatSaver (`/vr/beatsaver`) and Jobs (`/vr/jobs`). Other pages (About, New, BeatSaver playlists) keep their desktop path and get the VR styling. The immersive WebXR dashboard is a later phase with its own spec.

## Opening it

The layout is chosen in this order, first match wins:

1. the address: `/vr` and everything below it, or `?mode=vr`, is VR; `?mode=desktop` is desktop and beats the `/vr` path. Mode values are case-insensitive (`?mode=VR`, `/VR`, a stored `VR`); an unknown value or a lookalike path such as `/vrx` decides nothing;
2. the remembered choice, kept in the browser's local storage (blocked or garbage storage counts as nothing);
3. a standalone headset browser (Meta Quest Browser, Pico, Wolvic) is VR;
4. otherwise desktop. If the host helper reports a headset runtime, a toast titled "Headset in use: switch to VR layout?" stays at the bottom with Switch and Not now. Switch changes the layout and remembers the choice; Not now (or closing the toast) hides it for the session.

The VR / Desktop switch in the masthead (each button has an icon: headset, monitor) changes the layout and remembers it. Pages without a `/vr` path (About, New, BeatSaver playlists) keep their desktop path in either layout.

## Runtime detection: the host helper

The backend runs in a Linux container and cannot see host processes, so a small helper on the host reports which VR runtime is active.

1. Run `task st:vr-agent` on the host, outside Docker. It listens on `127.0.0.1:8101`; `--port N` changes the port and `--bind HOST` the address. It needs only Python and `uv`. With the optional `pyopenvr` package (`uv run --with openvr python scripts/vr_agent.py`) it also reports whether the headset is worn, read from the SteamVR activity level; without it `worn` is null.
2. `GET /status` answers `{"os", "runtime", "runtimes", "xr_runtime", "worn"}`. POST, PUT, DELETE, PATCH, OPTIONS and HEAD answer 405. The runtimes are SteamVR, Oculus, Virtual Desktop, Monado, WiVRn, ALVR; `runtime` is the first of `runtimes` in that order. Windows reads the process list and the OpenXR registry value, Linux reads `/proc/*/comm` and the OpenXR manifest, macOS has no PC VR runtime and always reports none.
3. The container asks the helper at `VR_AGENT_URL` (default `http://host.docker.internal:8101/status`; `docker-compose.yml` sets `extra_hosts: ["host.docker.internal:host-gateway"]`). The call has a 300 ms timeout and the answer is cached for 2 s. On Linux, Docker reaches the host through the bridge gateway, not loopback: start the helper with `--bind` set to the `docker0` address (usually `172.17.0.1`) or to the host's LAN address.
4. A backend run natively, outside a container, probes in-process and needs no helper.
5. `GET /api/vr/status` adds `source`: `agent`, `local` or `none`. The page polls it every 5 s while the tab is visible and stops while it is hidden.

If the helper is not running, nothing breaks: the status is "no runtime", no toast shows and `/vr` still works. If port 8101 is taken, the helper exits with a message that names `--port` and `VR_AGENT_URL`.

## LAN access for a standalone headset

A Quest, Pico or other standalone headset reaches saber-tooth over the network. This is off by default.

1. Set `SABER_BIND=0.0.0.0` in `.env` (default `127.0.0.1`) so the compose port listens on the network.
2. Set `SABER_ALLOWED_HOSTS` to the host names the headset uses, for example `SABER_ALLOWED_HOSTS=192.168.1.50`. A request whose `Host` is not listed is refused with 403 `{"error": "host not allowed"}`.
3. Open `http://<host>:8100/vr` in the headset browser.

Warning: saber-tooth has no login, so anyone on the network can fix, crop, download and permanently delete map folders while it is on. Turn `SABER_BIND` back to `127.0.0.1` when you are done.

## Crop steps in VR

VR mounts the desktop crop panel at the VR scale, so the chart handles, the 1 min and 2 min switch and the Save buttons work as on the desktop. There are no separate step buttons.

## Manual headset checklist

Run it for each of Oculus Dash, SteamVR Desktop and Virtual Desktop, with `task st:vr-agent` running and a few maps in the library.

1. Open `/vr` in the desktop browser the dashboard shows. The layout is large and high contrast.
2. Point the controller laser at a card and press the trigger. The Preview, Fix and Open buttons respond.
3. Scroll the list with the thumbstick. More cards load near the end.
4. Open a map and press Fix. The progress banner shows at the top at VR size; the Fixed copy appears.
5. Open the crop panel, switch 1 min and 2 min, drag the chart handles, then Save as new map (Save over this map asks for a confirmation first). "Cropped map written" appears with the new folder.
6. Open BeatSaver, press a preset and press Download on one map. It shows Installed afterwards.
7. With SteamVR running and `pyopenvr` installed, take the headset off and on: `worn` in `/api/vr/status` turns false and true.
8. Close the helper. The toast does not return after you chose Not now, `/vr` keeps working and the status shows no runtime.
