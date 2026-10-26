# Architecture

saber-tooth is one Python 3.12 process. FastAPI runs under uvicorn and serves the static frontend, a job worker runs in the same process, and state sits in SQLite.

## Quality bar

Modded gameplay must be as flawless, flowing and atmospheric as possible. Every generated map, fill and fix is held to this.

1. Flawless: zero findings from any check rule in every output difficulty. A proposal that cannot reach zero is not offered.
2. Flowing: natural parity, smooth position arcs, patterns that follow the phrasing of the music, fills that match their surroundings.
3. Atmospheric: lighting follows energy and structure, with strong shows on drops, calm on breaks, colour changes on section boundaries and a fitting environment.

Where these goals compete with implementation simplicity, the quality bar wins.

## Compose stack

1. `saber-tooth`: built from this repository, published on `127.0.0.1:${SABER_PORT:-8100}`.
   The container starts as root, `docker-entrypoint.sh` maps user `app` to `PUID`/`PGID` (default 1000), chowns `/data` only, and drops privileges with `setpriv`. `LEVELS_DIR` is never chowned and must be writable by `PUID`.
2. `beat-analyser`: image `levialabs/beat-analyser:latest`, internal network only, no published port.
3. Volumes:
   1. `CustomLevels` bind mount, read-write, at `/levels`. The host path comes from `LEVELS_DIR`.
   2. Named volume `analyser-uploads`, mounted at `/app/uploads` in beat-analyser and read-only at `/analyser` in saber-tooth.
   3. Named volume `saber-data` at `/data`: SQLite database, staging folders and the lightshow template index.

## Modules

The package is `src/saber_tooth/`. Each file stays under 300 lines. Larger parts are packages: `mapio`, `checks`, `generator`, `fixer`, `lightshow`, `service`, `api` and `web`.

1. `mapio`: parses Info v2 and v4 and difficulty v2, v3 and v4 into one internal model (`Map`, `Difficulty`, `Note`, `Bomb`, `Wall`, `BasicEvent`, `EventBoxGroup`, `ColorScheme`). Writes difficulty v3.3.0 and Info v2.1.0. Unknown keys are preserved when the source is v3, including `_fxEventsCollection`, which the `vfxEventBoxGroups` index into. Vanilla only: Mapping Extensions and Noodle values (x outside 0-3, y outside 0-2, cut direction outside 0-8) are unsupported and make the map unreadable with `MapParseError`. Any other failure while parsing a map is also reported as `MapParseError`, and a bpm that is not positive and finite is rejected.
2. `analyser`: HTTP client for beat-analyser (`upload`, `download_yt`), reader for a project folder (CSV parsing and metadata), and wav-to-ogg conversion through ffmpeg into `song.egg`.
3. `generator`: rule-based note placer. Inputs are the beat grid, kick, snare and hi-hat onsets, and bpm. A per-hand parity state machine picks cut directions. A per-difficulty profile sets notes per second, NJS, offset, minimum gap between same-hand swings and allowed patterns. The tempo map follows the analysed beats: it tracks the projected time of every grid beat under the tempo map built so far and emits a bpm event whenever the local tempo differs by more than 0.5 percent or the next beat would land more than 10 ms off, so the map stays within 10 ms of the audio. An analysis without kick, snare or hi-hat onsets is refused, and no difficulty may be generated empty.
4. `checks`: one pure function per rule. Each returns findings with rule id, difficulty, beat range, severity and note references.
5. `fixer`: turns each finding into a proposal with a minimal list of operations: `move`, `recolor`, `flip`, `delete`, `fill`, `add-difficulty`, `apply-lightshow`. A proposal stores a before and after excerpt.
6. `lightshow`: the learner indexes installed maps per environment and stores templates in `/data/lightshow.json`. The applier picks an environment and template, retimes it onto the beat grid, and emits basic events, v3 event box groups and a colour scheme.
7. `store`: SQLite tables `maps`, `jobs`, `proposals` and `scans`. Proposal status is `pending`, `approved`, `rejected` or `applied`. The `scans` table holds, per map, the findings of the last scan (the baseline) and the name of the analyser project used.
8. `service`: library refresh, scan, generate, apply and learn, over the store. The library is indexed at start and again whenever the set of folders under `/levels` changes, which `GET /api/maps` checks before it answers. Applying a map also refreshes it.
9. `jobs`: in-process worker with one thread. A job ends `done` or `failed`; a failed apply stores the conflicting proposal ids in its result.
10. `api`: FastAPI routes, described in [api.md](api.md). Every request whose `Host` is not `127.0.0.1`, `localhost`, `[::1]` (any port) or a name listed in the comma-separated `SABER_ALLOWED_HOSTS` gets 403, which stops DNS rebinding. Unsafe methods carrying an `Origin` header that differs from the host also get 403. Forwarded headers count only from peers listed in `SABER_TRUSTED_PROXY_IPS` (rightmost value; see [ADR 0009](adr/0009-configurable-user-and-proxy-trust.md)). Ids are matched against fixed patterns before any lookup.
11. `web`: static HTML and vanilla JS with a library view, a map detail view with findings and proposals, a before and after note timeline on a canvas, and a new-map form.

## Check rules

1. `parity-break`: the same hand swings in the same direction twice without a reset.
2. `wide-jump`: the same colour moves at least 2 columns or 2 rows within less than the minimum swing time of the difficulty.
3. `crossover`: red right of blue, or the reverse, in a way that forces arm crossing within a short window.
4. `vision-block`: a note in the two centre columns of the middle row hides notes that follow within the block window.
5. `stack-conflict`: same-colour notes at the same time with directions that cannot be cut in one swing.
6. `swing-speed`: a same-hand interval below the difficulty profile minimum.
7. `note-in-wall`: a note inside the lanes of an active wall.
8. `empty-gap`: at least N beats (default 8) without notes while onset density from the analysis exceeds a threshold.
9. `missing-difficulty`: one of the five Standard difficulties is absent.
10. `default-environment`: `DefaultEnvironment`, or no lighting events at all.
11. `wall-trap`: walls that leave fewer than 2 free lanes or block both centre lanes (error), or two walls that force a dodge to opposite sides closer than the profile dodge time (`WALL_DODGE_S`: Hard 0.8 s, Expert 0.6 s, ExpertPlus 0.45 s; warn, error below 60% of it). Crouch walls (`y` 2, height 3) never block lanes.
12. `wall-short`: a wall shorter than 0.12 s (warn).

## Walls

The generator adds walls only to Hard, Expert and ExpertPlus, never bombs. After the notes are final, `generator/walls.py` scans the per-bar energy: calm bars (energy below 0.45) and build-ups (energy rising over 4 bars) may get a wall at a bar start. A wall is a full-height side wall at lane 0 or 3, lasting 1 to 4 beats, with the side alternating per 4-bar phrase and flipped when notes occupy that lane. ExpertPlus may replace a build-up side wall with a crouch wall (`y` 2, width 2 at lane 1, height 3) when no note falls inside it. Spacing caps density: Hard one wall per 2 bars, Expert 1.5 bars, ExpertPlus 1 bar. Placement is deterministic per seed, and the `wall-trap`, `wall-short` and `note-in-wall` rules hold by construction. The fixer deletes a wall that a scan flags with `wall-trap` or `wall-short`.

## Finding identity

The fixer and apply decide whether a change added a problem by comparing findings before and after. Two findings are the same when their difficulty and rule match, the set of hand colours involved matches, and their beat ranges overlap or touch. The notes themselves are not part of the identity, because a valid fix moves, recolours or flips notes and would otherwise look like a new finding. See [ADR 0007](adr/0007-finding-identity-by-rule-colours-and-overlap.md).

## Data flow

1. New map:
   1. A URL or upload goes to beat-analyser.
   2. saber-tooth reads the analyser project folder from the shared volume.
   3. The generator builds five difficulties and the lightshow applier adds lights.
   4. The result is staged in `/data/staging/<job>`.
   5. A `create-map` proposal appears for review.
   6. On approval, the folder `st-<slug> (<Title> - saber-tooth)` is written to `/levels`.
2. Existing map:
   1. Scan runs the checks. Empty-gap detection first analyses the audio of the map with beat-analyser.
   2. Each finding becomes a pending proposal.
   3. The user approves or rejects each one, or approves all for the map.
   4. Apply copies the original folder to staging, merges the approved operations and re-runs the checks.
   5. The result is compared with the findings stored by the last scan. Any remaining error, or any finding that is not the same as a stored one, aborts apply, writes nothing and names the conflicting proposals.
   6. Otherwise staging is renamed to `<original name> [saber-tooth]` in `/levels`, and the Info `_songName` gains a ` [saber-tooth]` suffix.

## Error handling

1. beat-analyser unreachable or returning an error: the job state becomes `failed` with the upstream message.
2. An unparsable map is listed with a parse error. Scanning it answers 409.
3. All writes go to a temporary folder first, then an atomic rename into `/levels`.
4. A target folder name that already exists is refused. Re-applying after a previous apply writes to `<name> [saber-tooth 2]`.
5. Only YouTube URLs are accepted for generation, and uploads are limited by size and extension. See [ADR 0008](adr/0008-youtube-only-url-intake.md).
6. Nothing writes inside an original map folder. A test asserts this through a write guard in the filesystem layer.

## Testing

1. pytest with synthetic fixture maps (v2, v3, v4) under the tests fixtures folder. Tests never read the real `CustomLevels`.
2. Hypothesis properties: parse, write, parse round-trips the model; every generated difficulty passes every rule; applying a fix removes its finding and adds none.
3. beat-analyser is mocked with `httpx.MockTransport`.
4. API tests use the FastAPI `TestClient` with temporary `/levels` and `/data`.
5. One opt-in task scans a copy of real maps and prints counts. It is not part of the gate.

## beat-analyser project naming

1. `POST /upload` derives the project name from the uploaded filename: directory part dropped, extension dropped, then `secure_filename`. The result must match `[A-Za-z0-9][A-Za-z0-9._-]{0,99}`.
2. `POST /download_yt` uses the YouTube video id as the project name, validated against the same pattern.
3. Both routes answer with the zip as an attachment named `<name>_tracks.zip`, so the name is recoverable from `Content-Disposition`.
4. The client strips `_tracks.zip`, re-validates the name as one path component, resolves `uploads / name` and refuses any path outside `uploads`. The `GET /folders` fallback is not needed.
5. The client sends no `Origin` header; beat-analyser refuses cross-site POSTs only when `Origin` or `Sec-Fetch-Site` indicates one.

## Decisions

See [adr/README.md](adr/README.md).
