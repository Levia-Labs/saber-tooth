![saber-tooth logo](https://raw.githubusercontent.com/Levia-Labs/saber-tooth/main/docs/assets/logo.svg)

# saber-tooth

**Check, fix and generate Beat Saber custom levels from your own music.**

[![built on Crepidoma](https://img.shields.io/badge/built%20on-Crepidoma-6d28d9.svg)](https://github.com/Levia-Labs/Crepidoma)
[![licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](https://github.com/Levia-Labs/saber-tooth/blob/main/LICENSE)

Give it a song or an existing map and it writes a map folder into your `CustomLevels`
directory. It builds all five Standard difficulties, finds impossible swings, broken parity
and empty stretches in existing maps, and adds atmospheric lighting learned from the maps you
already have installed. It uses vanilla features only: no Chroma, Noodle Extensions or
Vivify. Every change is reviewed by you in the browser first, and fixes go into a new sibling
folder so the original map is never touched.

Source, issues and full documentation: <https://github.com/Levia-Labs/saber-tooth>

## Features

1. Library with status filters; once a map is fixed, its original is hidden.
2. One-click Fix writes `<map> [saber-tooth]` with all five Standard difficulties. Scan and Fix run in batches, save as they go and resume after a cancel, timeout or error.
3. Scan, Approve and Apply proposals, each verified to reach zero findings.
4. Map page with Status, Crop, Relight and Delete tabs and bottom toasts. The Status tab lists the findings and, after a Fix, why each unfixed finding was left.
5. Crop to a highlight (1 minute, 2 minutes or unlimited, free cutting down to 1 second) with an NPS chart, sections and playback; Auto crop proposes up to three windows; save as a new map or over the original.
6. Relight a map in another vanilla environment; the lightshow is regenerated and the fixes stay.
7. One-step generation from a YouTube link or a dropped audio file.
8. BeatSaver search, presets and downloads.
9. Playlists tab: build playlists from library maps, with SongCore hashes, `.bplist` export and sync URLs that PlaylistManager refreshes on its own.
10. Jobs tab: what the server is running, what waits and what finished in the last day, with cancel, retry and restart; queued jobs survive a restart.
11. Settings tab: how many fix and scan jobs run at once, shown with the cores and memory the container has, and a PlaylistManager check with a one-click install from BeatMods.
12. VR mode at `/vr`, with a host helper that detects the headset; desktop, VR and mobile layouts.
13. About page.
14. MCP tools for agents.

## Screenshots

![The library with status filters](https://raw.githubusercontent.com/Levia-Labs/saber-tooth/main/docs/screenshots/library.png)

![The crop view with the NPS chart, sections and playback](https://raw.githubusercontent.com/Levia-Labs/saber-tooth/main/docs/screenshots/map-crop.png)

![BeatSaver search results](https://raw.githubusercontent.com/Levia-Labs/saber-tooth/main/docs/screenshots/beatsaver.png)

![The VR library screen](https://raw.githubusercontent.com/Levia-Labs/saber-tooth/main/docs/screenshots/vr-library.png)

## How it works

1. A song (YouTube URL or uploaded audio file) or an existing map goes in.
2. The [beat-analyser](https://github.com/Levia-Labs/beat-analyser) sidecar downloads
   the audio and returns the beat grid and onsets.
3. The generator places notes, the checks look for problems, and the fixer proposes repairs,
   each verified to reach zero findings before it is offered.
4. You review each proposal on a timeline in the browser.
5. Approved changes are written as a new map folder in `CustomLevels`.
6. **FastAPI** serves a React web UI, a JSON API and an MCP endpoint on port 8100. **ffmpeg**
   is built into the image.

## Quick start

The service needs beat-analyser next to it. Save this as `docker-compose.yml`:

```yaml
services:
  saber-tooth:
    image: levialabs/sabertooth:latest
    ports: ["127.0.0.1:8100:8100"]
    environment:
      LEVELS_DIR: /levels
      DATA_DIR: /data
      ANALYSER_URL: http://beat-analyser:8000
      ANALYSER_UPLOADS: /analyser
      PUID: 1000
      PGID: 1000
    volumes:
      - "/path/to/Beat Saber_Data/CustomLevels:/levels"
      - analyser-uploads:/analyser:ro
      - saber-data:/data
    depends_on:
      beat-analyser:
        condition: service_healthy
  beat-analyser:
    image: levialabs/beat-analyser:latest
    volumes: ["analyser-uploads:/app/uploads"]
    read_only: true
    tmpfs: ["/tmp"]
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/folders', timeout=4)
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 20s
volumes:
  analyser-uploads:
  saber-data:
```

Then run `docker compose up -d` and open <http://127.0.0.1:8100>.

The container starts as root only to apply `PUID` and `PGID`, then drops to that user. It
never changes ownership of `/levels`: on Linux, the mounted levels folder must be writable by
the `PUID` user.

The source repository has the full `docker-compose.yml` with the optional settings, including
the Playlists folder.

## Volumes

| Mount        | Purpose                                                                |
| ------------ | ---------------------------------------------------------------------- |
| `/levels`    | Your `CustomLevels` folder. Maps are read here and new folders written |
| `/data`      | Service state: scan results, proposals, caches, learned lightshows     |
| `/analyser`  | beat-analyser's uploads volume, mounted read-only to read its output   |
| `/playlists` | Optional. Beat Saber Playlists folder for `.bplist` export             |

## Configuration

| Variable                  | Default                     | Meaning                                                                        |
| ------------------------- | --------------------------- | ------------------------------------------------------------------------------ |
| `LEVELS_DIR`              | `/levels`                   | Where the service reads and writes maps                                        |
| `DATA_DIR`                | `/data`                     | Where the service keeps its own state                                          |
| `ANALYSER_URL`            | `http://beat-analyser:8000` | Base URL of the beat-analyser service                                          |
| `ANALYSER_UPLOADS`        | `/analyser`                 | Where beat-analyser's output volume is mounted                                 |
| `PLAYLISTS_DIR`           | unset                       | Playlists folder; setting it enables the `.bplist` export                      |
| `MAX_UPLOAD_MB`           | `200`                       | Largest audio upload                                                           |
| `SABER_ALLOWED_HOSTS`     | empty                       | Extra `Host` names accepted besides `127.0.0.1`, `localhost` and `[::1]`       |
| `SABER_TRUSTED_PROXY_IPS` | empty                       | Comma list of single proxy addresses whose `X-Forwarded-*` headers are trusted |
| `PUID`, `PGID`            | `1000`                      | User and group the service runs as                                             |
| `VR_AGENT_URL`            | unset                       | VR headset helper; compose default `http://host.docker.internal:8101/status`   |
| `SABER_BIND`              | `127.0.0.1`                 | Host address of the published port (compose); `0.0.0.0` opens it to the LAN    |

Warning: with `SABER_BIND=0.0.0.0` anyone on the network can fix, crop, download and permanently delete map folders, because the service has no login. Also set `SABER_ALLOWED_HOSTS` to the names the headset uses, and set `SABER_BIND` back to `127.0.0.1` when done. See [VR mode](https://github.com/Levia-Labs/saber-tooth/blob/main/docs/vr.md).

`MAX_UPLOAD_MB` and `YT_MAX_MINUTES` (default `20`) also apply to the beat-analyser container.

## API and MCP

The REST API lives under `/api`. Routes that start work answer `{"job": "<id>"}`; poll
`GET /api/jobs/{id}` until `status` is `done` or `failed`.

| Method | Path                       | Does                                                          |
| ------ | -------------------------- | ------------------------------------------------------------- |
| GET    | `/api/health`              | `{"status": "ok"}`, the container health check                |
| GET    | `/api/maps`                | One page of the library, with search, sort and filters        |
| POST   | `/api/maps/{id}/scan`      | Check one map                                                 |
| POST   | `/api/maps/{id}/fix`       | One-click fix, written to a new `<name> [saber-tooth]` folder |
| POST   | `/api/generate`            | New map from a YouTube URL or an uploaded audio file          |
| GET    | `/api/maps/{id}/proposals` | Proposed changes for a map, with before and after excerpts    |
| POST   | `/api/maps/{id}/apply`     | Write the approved proposals into a new sibling folder        |
| POST   | `/api/lightshow/learn`     | Learn lightshow styles from the installed maps                |
| GET    | `/api/beatsaver/search`    | Search BeatSaver                                              |
| POST   | `/api/beatsaver/download`  | Install up to 100 BeatSaver maps as new folders               |

Errors are JSON: `{"error": "..."}`. The route list is longer than this table; see the
[API reference](https://github.com/Levia-Labs/saber-tooth/blob/main/docs/api.md).

Agents can connect over MCP (Streamable HTTP) at `/mcp`:

```bash
claude mcp add --transport http saber-tooth http://127.0.0.1:8100/mcp
```

Tools: `list_maps`, `get_proposals`, `scan_map`, `job_status`, `approve_proposal`,
`reject_proposal`, `apply_map`, `generate_from_youtube`, `learn_lightshows`, `map_timeline`,
`crop_map`, `beatsaver_search` and `beatsaver_download`. Details are in the
[MCP section](https://github.com/Levia-Labs/saber-tooth/blob/main/docs/api.md#mcp).

## Security

The API has no authentication. Publish the port on `127.0.0.1` (as above) unless the service
sits behind something that authenticates. Requests with a `Host` outside the allowlist get
403, and state-changing requests whose `Origin` does not match are refused. Behind a TLS
proxy, set `SABER_ALLOWED_HOSTS` and `SABER_TRUSTED_PROXY_IPS`. Fixes are written to a new
folder and the original map is never changed.

## Tags

| Tag      | What it is                |
| -------- | ------------------------- |
| `1.3.0`  | The 1.3.0 release         |
| `latest` | The same build as `1.3.0` |
| `1.2.0`  | The 1.2.0 release, kept   |
| `1.1.0`  | The 1.1.0 release, kept   |
| `1.0.0`  | The 1.0.0 release, kept   |

## Limits

1. Standard characteristic only: the five Standard difficulties are generated and checked.
2. Vanilla features only. Maps that require Noodle or Mapping Extensions are refused on
   BeatSaver download.
3. Map generation needs beat-analyser; YouTube downloads need outbound internet.
4. Only YouTube URLs are accepted for generation. Other sites are refused.
5. The service is built for a single user on localhost.

## Part of Levia Labs

1. [beat-analyser](https://github.com/Levia-Labs/beat-analyser): the audio download and
   beat and onset analysis service that saber-tooth runs next to.
2. [Crepidoma](https://github.com/Levia-Labs/Crepidoma): the base every Levia Labs project
   stands on, a Claude Code plugin with shared Task namespaces, configs and ADRs.
3. [Levia-Labs on GitHub](https://github.com/Levia-Labs): every public project.

## Licence

MIT.
