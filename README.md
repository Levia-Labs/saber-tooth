# saber-tooth

saber-tooth is a Docker service that creates and repairs Beat Saber custom maps. You drive it through an HTTP API or a plain HTML page. It writes map folders into the `CustomLevels` directory of the game, and the game does not need the service to run.

## What it does

1. Generates a new map from a YouTube URL or an uploaded audio file, with all five Standard difficulties: Easy, Normal, Hard, Expert and ExpertPlus.
2. Finds impossible sections in existing maps, such as same-colour notes on opposite sides of the grid too close in time to swing between, and proposes fixes.
3. Finds long empty stretches where the music has onsets, and proposes fills.
4. Learns how installed maps reach modern visuals with vanilla features (environment, v3 event boxes, colour schemes) and applies the same technique to maps that have none.
5. Changes nothing until you approve it. Fixes to existing maps go into a new sibling folder, and the original is never written.

Only vanilla features are used. No Chroma, Noodle Extensions, Vivify or Heck requirement is ever added.

## Quality bar

Modded gameplay must be as flawless, flowing and atmospheric as possible. Every generated map, fill and fix is accepted or rejected on this.

1. Flawless: zero findings from any check rule in every output difficulty. A proposal that cannot reach zero is not offered.
2. Flowing: swings follow natural parity, positions move in smooth arcs, and patterns follow the phrasing of the music. Fills match the density and style around them.
3. Atmospheric: lighting follows the energy and structure of the song. Strong shows on drops, calm on breaks, colour changes at section boundaries, and an environment that fits the song.

When these goals compete with simplicity of implementation, the quality bar wins.

## Quick start

1. Copy `.env.example` to `.env` and set `LEVELS_DIR` to your `CustomLevels` folder.
2. Run `task st:up`.
3. Open `http://127.0.0.1:8100` (or the port in `SABER_PORT`).
4. Stop the stack with `task st:down`.

## Tasks

1. `task st:up` and `task st:down`: build and start, or stop, the compose stack.
2. `task st:logs`: show the last 100 log lines of the saber-tooth container.
3. `task st:test`: run the pytest suite.
4. `task st:check -- <folder>`: run the quality checks on one map folder.
5. `task st:inspect -- <folder>`: summarise one map folder.
6. `task st:survey -- <levels_dir>`: read-only finding counts across a levels directory.
7. `task st:learn -- <levels_dir> <out.json>`: build lightshow templates.
8. `task st:gen -- <url>`: start a map generation job from a URL.
9. `task --list`: every task, including the `lint:`, `quality:` and `claude:` groups from Crepidoma.

## Configuration

1. `LEVELS_DIR`: host path of `CustomLevels`, mounted read-write at `/levels`.
2. `SABER_PORT`: host port on `127.0.0.1`, default 8100.
3. `YT_MAX_MINUTES`: longest accepted YouTube video, default 20.
4. `MAX_UPLOAD_MB`: largest accepted audio upload, default 200.

## Documentation

1. [Architecture](docs/architecture.md)
2. [API](docs/api.md)
3. [Map format](docs/map-format.md)
4. [Decision records](docs/adr/README.md)
5. [Design spec](docs/superpowers/specs/2026-10-26-saber-tooth-design.md)

## Status

The scaffold, tooling and documentation exist. The following parts of the design are not built yet.

1. Map IO for v2, v3 and v4 (planned).
2. Checks and fixer (planned).
3. Generator (planned).
4. Lightshow learner and applier (planned).
5. API, store and web frontend (planned).
6. Compose stack (planned).
