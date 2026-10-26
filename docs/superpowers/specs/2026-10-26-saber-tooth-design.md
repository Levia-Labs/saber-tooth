# saber-tooth design

Date: 2026-10-26. Status: approved in conversation, pending written-spec review.

## Goal

A Docker service with an HTTP API and a plain HTML frontend that creates and repairs Beat Saber custom maps. It writes map folders into the game's `CustomLevels` directory. Running the game is independent of the service.

## Requirements

1. Generate a new map from a YouTube URL or an uploaded audio file. The `beat-analyser` container performs the download and the beat analysis.
2. Every map saber-tooth produces has all five Standard difficulties: Easy, Normal, Hard, Expert, ExpertPlus.
3. Detect impossible sections in existing maps (for example, same-colour notes on opposite sides of the grid within a window too short to swing between them) and propose fixes.
4. Detect empty sections: long stretches without notes while the music has onsets. Propose fills.
5. Learn how installed maps achieve modern visuals with vanilla features (environment choice, v3 event-box lighting, colour schemes). Apply that technique to maps that use `DefaultEnvironment` or have no lighting.
6. Vanilla only. No Chroma, Noodle Extensions, Vivify, Heck or any other gameplay or visual mod requirement or suggestion is added.
7. Every change is a proposal that the user approves before it is written.
8. Fixes to existing maps go into a new sibling folder. The original folder is never written.

## Non-goals

1. Launching or controlling the game.
2. Machine-learning map generation.
3. Multi-user access, authentication, or exposure beyond localhost.
4. Lightshow-only (`Lightshow` characteristic) or non-Standard characteristics such as OneSaber, 360 and 90 degree.

## Environment facts

1. Game version 1.45.3 at `X:\SteamLibrary\steamapps\common\Beat Saber`. About 150 maps in `Beat Saber_Data\CustomLevels`.
2. Map files in the wild: `Info.dat` or `info.dat`. Difficulty files are named `<Diff>.dat`, `<Diff>Standard.dat` or `<Diff>.beatmap.dat`. Audio is `.egg` or `.ogg`. Covers are `.jpg` or `.png`.
3. Formats in the wild: Info v2.0.0 and v2.1.0 (some v4). Difficulties are v2 (`_notes`), v3 (`colorNotes`) and v4 (with separate lightshow files).
4. `beat-analyser` (Flask, port 8000 in the container) exposes `POST /upload` (multipart `file`), `POST /download_yt` (JSON `{"url"}`), `GET /folders` and `GET /download/<name>`. It stores each project in `/app/uploads/<name>/` with `audio.wav`, `meta.json` (`name`, `key`, `bpm`), `labels.json` and header-less CSVs (`time,label_id`): `beats`, `kick`, `snare`, `hh`, `bass`, `melody`, `chords`. It rejects POSTs with a foreign `Origin` header; server-to-server calls send none.

## Architecture

Single Python 3.12 process (FastAPI under uvicorn) with an in-process job worker and a SQLite store. Static frontend served by the same process.

### Compose

1. `saber-tooth`: built from this repo, published on `127.0.0.1:${SABER_PORT:-8100}`.
2. `beat-analyser`: image `levialabs/beat-analyser:latest`, internal network only, no published port.
3. Volumes:
   1. `CustomLevels` bind mount, read-write, at `/levels`. Host path from `LEVELS_DIR` in `.env`.
   2. Named volume `analyser-uploads` mounted at `/app/uploads` in beat-analyser and read-only at `/analyser` in saber-tooth.
   3. Named volume `saber-data` at `/data`: SQLite database, staging folders, lightshow template index.

### Modules

Package `src/saber_tooth/`. Each file stays under 300 lines.

1. `mapio`: parse Info v2/v4 and difficulty v2/v3/v4 into one internal model (`Map`, `Difficulty`, `Note`, `Bomb`, `Wall`, `BasicEvent`, `EventBoxGroup`, `ColorScheme`). Write difficulty v3.3.0 and Info v2.1.0 (`_environmentNames`, `_colorSchemes`, `_environmentNameIdx`, `_beatmapColorSchemeIdx`). Unknown keys are preserved when the source is v3.
2. `analyser`: HTTP client for beat-analyser (`upload`, `download_yt`), reader for a project folder (CSV parsing, meta), and wav-to-ogg conversion through ffmpeg into `song.egg`.
3. `generator`: rule-based placer. Inputs: beat grid, kick, snare, hi-hat onsets, bpm. A per-hand parity state machine (forehand or backhand) chooses cut directions. Positions follow flow rules (no resets without a bomb, reachable distance per swing). A per-difficulty profile sets target notes per second, NJS, offset, minimum gap between same-hand swings, and allowed patterns (Easy: singles only on strong beats; ExpertPlus: streams, doubles, crossovers forbidden).
4. `checks`: one pure function per rule. Each returns findings with rule id, difficulty, beat range, severity and note references. Rules:
   1. `parity-break`: same hand swings in the same direction twice without a reset.
   2. `wide-jump`: same colour moves at least 2 columns or 2 rows within less than the difficulty's minimum swing time.
   3. `crossover`: red right of blue (or the reverse) in a way that forces arm crossing within a short window.
   4. `vision-block`: a note in the centre two columns of the middle row hides notes that follow within the block window.
   5. `stack-conflict`: same colour notes at the same time with directions that cannot be cut in one swing.
   6. `swing-speed`: same-hand interval below the difficulty profile minimum.
   7. `note-in-wall`: a note inside an active wall's lanes.
   8. `empty-gap`: at least N beats (default 8) with no notes while onset density from the analysis exceeds a threshold.
   9. `missing-difficulty`: one of the five Standard difficulties is absent.
   10. `default-environment`: `DefaultEnvironment`, or no lighting events at all.
5. `fixer`: turns each finding into a proposal holding a minimal list of operations: `move`, `recolor`, `flip`, `delete`, `fill` (generator constrained to neighbouring parity and density), `add-difficulty` (thin a denser difficulty or generate), `apply-lightshow`. A proposal stores a before and after excerpt.
6. `lightshow`:
   1. Learner: index local maps per environment. It records event types used, event-box-group shapes (group ids, filters, distributions), events per beat and colour schemes, then stores templates in `/data/lightshow.json`.
   2. Applier: chooses an environment and template for the target map and retimes it onto the beat grid. Kicks drive strobes, energy changes drive colour shifts. It emits basic events plus event box groups in v3 form and sets a colour scheme.
7. `store`: SQLite tables `maps`, `jobs`, `proposals` (status `pending`, `approved`, `rejected`, `applied`).
8. `api`: FastAPI routes listed below.
9. `web`: static HTML and vanilla JS. Views: library, map detail with findings and proposals, before/after note timeline drawn on a canvas, new-map form.

### API

1. `GET /api/maps`: library with finding counts.
2. `POST /api/maps/{id}/scan`: run checks, create proposals.
3. `GET /api/maps/{id}/proposals`: proposals with before and after excerpts.
4. `POST /api/proposals/{id}/approve` and `/reject`.
5. `POST /api/maps/{id}/approve-all`: explicit bulk approval for one map.
6. `POST /api/maps/{id}/apply`: write approved proposals into the sibling folder.
7. `POST /api/generate`: body `{"url"}` or multipart file. Starts a job that ends in a `create-map` proposal.
8. `POST /api/lightshow/learn`: rebuild the template index.
9. `GET /api/jobs/{id}`: job status and error.

## Data flow

1. New map:
   1. URL or upload goes to beat-analyser.
   2. saber-tooth reads the analyser project folder.
   3. The generator builds five difficulties and the lightshow applier adds lights.
   4. The result is staged in `/data/staging/<job>`.
   5. A `create-map` proposal appears for review.
   6. On approval, the folder `st-<slug> (<Title> - saber-tooth)` is written to `/levels`.
2. Existing map:
   1. Scan runs the checks. Empty-gap detection first analyses the map's audio with beat-analyser (uploaded as `.ogg`).
   2. Each finding becomes a pending proposal.
   3. The user approves or rejects each one, or approves all for the map.
   4. Apply copies the original folder to staging, merges the approved operations, and re-runs the checks.
   5. If any applied operation produces a new finding, apply aborts and reports it.
   6. Otherwise staging is renamed to `<original name> [saber-tooth]` in `/levels`. The Info `_songName` gains a ` [saber-tooth]` suffix so both versions are distinguishable in game.

## Error handling

1. beat-analyser unreachable or returning an error: job state `failed` with the upstream message.
2. Unparsable map: listed with a parse error, skipped by scan.
3. All writes go to a temporary folder first, then an atomic rename into `/levels`.
4. A target folder name that already exists is refused. Re-applying after a previous apply writes to `<name> [saber-tooth 2]`.
5. Nothing ever writes inside an original map folder. A test asserts this through a write guard in the filesystem layer.

## Testing

1. pytest. Synthetic fixture maps (v2, v3, v4) live under `tests/fixtures/`; tests never read the real `CustomLevels`.
2. Hypothesis property tests:
   1. Parse then write then parse round-trips the internal model.
   2. Every generated difficulty passes every check rule.
   3. Applying a fix removes its finding and adds no new finding.
3. beat-analyser is mocked with `httpx.MockTransport`.
4. API tests use FastAPI `TestClient` with a temporary `/levels` and `/data`.
5. One opt-in task scans a copy of real maps and prints counts; it is not part of the gate.

## Repository tooling

1. Crepidoma adopted per `X:\Projects\Crepidoma\docs\migration.md`: `.crepidoma` submodule, Taskfile includes, plugin settings, pre-commit, CLAUDE.md.
2. `tasks/` Taskfile namespace `st` with: `up`, `down`, `logs`, `scan -- <map>`, `check -- <folder>`, `gen -- <url>`, `learn`, `test`.
3. `.claude/`: agents `map-auditor` (runs checks on one folder, returns counts) and `lightshow-learner`, a project README listing agents, skills and plugins.
4. Docs: `README.md`, `TODO.md`, `docs/architecture.md`, `docs/map-format.md`, `docs/api.md`, `docs/adr/`.

## Decisions (ADRs)

1. 0001 Vanilla-only visuals.
2. 0002 Output format: difficulty v3.3.0 and Info v2.1.0.
3. 0003 Sibling-folder output and approval gate.
4. 0004 Rule-based generator.
5. 0005 beat-analyser integration through a shared volume.
6. 0006 Single-process FastAPI with SQLite.
