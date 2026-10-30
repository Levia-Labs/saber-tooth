<p align="center"><img src="docs/assets/logo.svg" alt="saber-tooth" width="480"></p>

# saber-tooth

![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Docker](https://img.shields.io/badge/docker-compose-2496ED)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Generate and repair Beat Saber maps from your own music, with every change reviewed by you first.

saber-tooth is a local Docker service with a browser interface. Give it a song or an existing map and it writes a map folder into your `CustomLevels` directory. It builds all five Standard difficulties, finds impossible and empty sections in existing maps, and adds atmospheric lighting learned from the maps you already have installed. It uses vanilla features only, so no Chroma, Noodle Extensions or Vivify is ever required. The game does not need the service to run.

## Features

1. Library with status filters; once a map is fixed, its original is hidden.
2. One-click Fix writes `<map> [saber-tooth]` with all five Standard difficulties (Easy, Normal, Hard, Expert, ExpertPlus). The original map is never touched.
3. Scan, Approve and Apply proposals: checks for impossible swings, broken parity and empty stretches, with fixes verified to reach zero findings before they are offered.
4. Map page with Status, Crop and Delete tabs; results show as toasts at the bottom.
5. Crop to a highlight of 1 minute, 2 minutes or unlimited length, with free cutting down to 1 second. An NPS chart with sections, playback, and saving as a new map or over the original.
6. One-step map generation from a YouTube link or a dropped audio file, analysed by the beat-analyser sidecar.
7. BeatSaver search, presets, playlists and downloads.
8. VR mode with `/vr` screens and a headset detection helper (`task st:vr-agent`); see [VR mode](docs/vr.md).
9. Lighting that follows the energy and structure of the song, from a bundled learned set; "Learn lightshows" adds the styles of your installed maps.
10. Jobs tab: what the server is running, what waits (with cancel) and what finished in the last day; queued jobs survive a restart.
11. Settings tab: how many fix and scan jobs run at once (with the cores and memory the container has), and a PlaylistManager check with a one-click install from BeatMods; needs `GAME_DIR_HOST` for the install.
12. MCP tools for agents, and a compose stack with beat-analyser. Vanilla features only: no Chroma, Noodle Extensions or Vivify.

## Screenshots

1. ![The library with status filters](docs/screenshots/library.png)
2. ![The crop view with the NPS chart, sections and playback](docs/screenshots/map-crop.png)
3. ![BeatSaver search results](docs/screenshots/beatsaver.png)
4. ![The VR library screen](docs/screenshots/vr-library.png)

## How it works

1. A song or an existing map goes in.
2. [beat-analyser](https://github.com/Levia-Labs/beat-analyser) downloads the audio and returns the beat grid and onsets.
3. The generator places notes, the checks look for problems, and the fixer proposes repairs.
4. You review each proposal on a timeline in the browser.
5. A generated map is written, fixed, straight into `CustomLevels`; approved fixes to an existing map are written as a new folder.

The design goals are flawless, flowing and atmospheric maps. See the [design spec](docs/superpowers/specs/2026-10-26-saber-tooth-design.md) for the quality bar.

## Quick start

1. Copy `.env.example` to `.env` and set `LEVELS_DIR` to your `CustomLevels` folder.
2. Run `task st:up`.
3. Open <http://127.0.0.1:8100>, or the port set in `SABER_PORT`.
4. Run `task st:stop` to pause (containers kept) and `task st:start` to resume. `task st:down` removes the containers; volumes and images stay.
5. Agents can connect over MCP: `claude mcp add --transport http saber-tooth http://127.0.0.1:8100/mcp`. See [API](docs/api.md#mcp).
6. On Linux, set `PUID` and `PGID` in `.env` to the owner of `LEVELS_DIR` (default 1000). The container never changes ownership of `LEVELS_DIR`; it must be writable by that uid.

## Common tasks

| Task                                       | Purpose                                             |
| ------------------------------------------ | --------------------------------------------------- |
| `task st:up`                               | Build if needed and start; reuses cached layers     |
| `task st:stop` / `task st:start`           | Pause or resume; containers and volumes kept        |
| `task st:down`                             | Remove the containers; volumes and images kept      |
| `task st:logs`                             | Show recent container logs                          |
| `task st:test`                             | Run the pytest suite                                |
| `task st:web:build` / `task st:web:test`   | Build the frontend into the app; run its tests      |
| `task st:check -- <folder>`                | Run the quality checks on one map folder            |
| `task st:inspect -- <folder>`              | Summarise one map folder                            |
| `task st:survey -- <levels_dir>`           | Count findings across a levels directory, read-only |
| `task st:learn -- <levels_dir> <out.json>` | Build lightshow templates                           |
| `task st:learn-bundle -- <levels_dir>`     | Regenerate the bundled lightshow set                |
| `task st:gen -- <url>`                     | Start a generation job from a URL                   |
| `task st:gate`                             | Run every validation gate, one line each            |
| `task st:lane -- <name>`                   | Create a work lane worktree; see the workflow doc   |
| `task st:commit -- -m "<msg>" <paths>`     | Format, stage and commit exactly those paths        |
| `task st:review-diff -- <range>`           | Write a lockfile-free review diff                   |
| `task st:sync`                             | One-line state of every worktree                    |
| `task st:smoke`                            | Smoke-check the running stack                       |
| `task st:browser-check`                    | Headless Chrome or Firefox page check               |
| `task st:docker-health`                    | Compose service health and recent logs              |
| `task st:vr-agent`                         | Run the VR runtime helper on the host (port 8101)   |

Run `task --list` for every task. Settings (`LEVELS_DIR`, `SABER_PORT`, `SABER_BIND`, `VR_AGENT_URL`, `YT_MAX_MINUTES`, `MAX_UPLOAD_MB`) are documented in `.env.example`.

## Status

Version 1.1.0. Open work is tracked in [TODO.md](TODO.md).

## Part of Levia Labs

1. [beat-analyser](https://github.com/Levia-Labs/beat-analyser): the audio download and beat and onset analysis service that saber-tooth runs next to.
2. [Crepidoma](https://github.com/Levia-Labs/Crepidoma): the shared engineering foundation behind this repo, with Taskfiles, hooks, agents and quality gates.

## Documentation

1. [Architecture](docs/architecture.md)
2. [API](docs/api.md)
3. [Map format](docs/map-format.md)
4. [Decision records](docs/adr/)
5. [Workflow](docs/workflow.md)
6. [VR mode](docs/vr.md)
7. [TODO](TODO.md)

## License

MIT. See [LICENSE](LICENSE).
