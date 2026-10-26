# Architecture

saber-tooth is one Python 3.12 process: FastAPI under uvicorn, an in-process job worker, a SQLite store, and a static frontend served by the same process.

## Quality bar

Modded gameplay must be as flawless, flowing and atmospheric as possible. This applies to every generated map, fill and fix.

1. Flawless: zero findings from any check rule in every output difficulty. A proposal that cannot reach zero is not offered.
2. Flowing: natural parity, smooth position arcs, patterns that follow the phrasing of the music, fills that match their surroundings.
3. Atmospheric: lighting follows energy and structure, with strong shows on drops, calm on breaks, colour changes on section boundaries and a fitting environment.

Where these goals compete with implementation simplicity, the quality bar wins.

## Compose stack

1. `saber-tooth`: built from this repository, published on `127.0.0.1:${SABER_PORT:-8100}`.
2. `beat-analyser`: image `levialabs/beat-analyser:latest`, internal network only, no published port.
3. Volumes:
   1. `CustomLevels` bind mount, read-write, at `/levels`. The host path comes from `LEVELS_DIR`.
   2. Named volume `analyser-uploads`, mounted at `/app/uploads` in beat-analyser and read-only at `/analyser` in saber-tooth.
   3. Named volume `saber-data` at `/data`: SQLite database, staging folders and the lightshow template index.

## Modules

The package is `src/saber_tooth/`. Each file stays under 300 lines.

1. `mapio`: parses Info v2 and v4 and difficulty v2, v3 and v4 into one internal model (`Map`, `Difficulty`, `Note`, `Bomb`, `Wall`, `BasicEvent`, `EventBoxGroup`, `ColorScheme`). Writes difficulty v3.3.0 and Info v2.1.0. Unknown keys are preserved when the source is v3.
2. `analyser`: HTTP client for beat-analyser (`upload`, `download_yt`), reader for a project folder (CSV parsing and metadata), and wav-to-ogg conversion through ffmpeg into `song.egg`.
3. `generator`: rule-based note placer. Inputs are the beat grid, kick, snare and hi-hat onsets, and bpm. A per-hand parity state machine picks cut directions. A per-difficulty profile sets notes per second, NJS, offset, minimum gap between same-hand swings and allowed patterns.
4. `checks`: one pure function per rule. Each returns findings with rule id, difficulty, beat range, severity and note references.
5. `fixer`: turns each finding into a proposal with a minimal list of operations: `move`, `recolor`, `flip`, `delete`, `fill`, `add-difficulty`, `apply-lightshow`. A proposal stores a before and after excerpt.
6. `lightshow`: the learner indexes installed maps per environment and stores templates in `/data/lightshow.json`. The applier picks an environment and template, retimes it onto the beat grid, and emits basic events, v3 event box groups and a colour scheme.
7. `store`: SQLite tables `maps`, `jobs` and `proposals`. Proposal status is `pending`, `approved`, `rejected` or `applied`.
8. `api`: FastAPI routes, described in [api.md](api.md).
9. `web`: static HTML and vanilla JS with a library view, a map detail view with findings and proposals, a before and after note timeline on a canvas, and a new-map form.

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
   5. If any applied operation produces a new finding, apply aborts and reports it.
   6. Otherwise staging is renamed to `<original name> [saber-tooth]` in `/levels`, and the Info `_songName` gains a ` [saber-tooth]` suffix.

## Error handling

1. beat-analyser unreachable or returning an error: the job state becomes `failed` with the upstream message.
2. An unparsable map is listed with a parse error and skipped by scan.
3. All writes go to a temporary folder first, then an atomic rename into `/levels`.
4. A target folder name that already exists is refused. Re-applying after a previous apply writes to `<name> [saber-tooth 2]`.
5. Nothing writes inside an original map folder. A test asserts this through a write guard in the filesystem layer.

## Testing

1. pytest with synthetic fixture maps (v2, v3, v4) under the tests fixtures folder. Tests never read the real `CustomLevels`.
2. Hypothesis properties: parse, write, parse round-trips the model; every generated difficulty passes every rule; applying a fix removes its finding and adds none.
3. beat-analyser is mocked with `httpx.MockTransport`.
4. API tests use the FastAPI `TestClient` with temporary `/levels` and `/data`.
5. One opt-in task scans a copy of real maps and prints counts. It is not part of the gate.

## Decisions

See [adr/README.md](adr/README.md).
