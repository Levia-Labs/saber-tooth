# BeatSaver integration design

Date: 2026-10-27. Status: design approved in conversation; written spec pending review.

## Goal

Find and download BeatSaver maps that the BeatSaver website cannot filter for, from inside saber-tooth, and bring
them into the library ready to scan.

## User requirements

1. A BeatSaver view next to the Library, reached by a switch button in the header, with its own URL.
2. Search BeatSaver maps and BeatSaver playlists ("collections"); filter easily; download single maps or whole
   selections.
3. The critical saved search (first preset):
   1. Easy, Normal and Hard all present in the Standard characteristic (Expert and Expert+ optional).
   2. Rating at least 95 percent (BeatSaver `stats.score >= 0.95`).
   3. At least one difficulty with notes per second between 1 and 2 inclusive.
   4. Any of the tags: electronic, dubstep, rock, metal, punk, j-rock, techno, house, trance, drum-and-bass.
4. Downloads go into CustomLevels as new folders and appear in the library; nothing existing is overwritten.

## BeatSaver API facts used (from api.beatsaver.com OpenAPI spec)

1. `GET /search/text/{page}` with `q` (may be empty), `order` (Latest, Relevance, Rating, Curated, Random, Duration),
   `ascending`, `tags` (`,` AND, `|` OR, `!` exclude), `minRating`/`maxRating`, `minNps`/`maxNps`, `minBpm`/`maxBpm`,
   `minDuration`/`maxDuration`, `fullSpread`, `leaderboard` (All, Ranked, BeatLeader, ScoreSaber), `characteristics`,
   `environments`, `from`/`to`, `curated`, `verified`, `automapper`, `chroma`, `noodle`, `me`, `cinema`, `vivify`,
   `pageSize`.
2. `GET /maps/id/{id}`, `GET /maps/ids/{ids}` (up to 50), `GET /maps/hash/{hash}` (up to 50).
3. Playlists: `GET /playlists/search/{page}` (`q`, `order`, `minNps`, `maxNps`, `curated`, `verified`,
   `includeEmpty`, `from`, `to`, `ascending`), `GET /playlists/id/{id}/{page}`, `GET /playlists/user/{userId}/{page}`.
4. MapDetail: `id`, `name`, `uploader.name`, `metadata` (`bpm`, `duration`, `songName`, `songSubName`,
   `songAuthorName`, `levelAuthorName`), `stats` (`score`, `upvotes`, `downvotes`, `downloads`), `tags[]`, `ranked`
   flags, `versions[]` (`hash`, `state`, `downloadURL`, `coverURL`, `previewURL`, `diffs[]` with `difficulty`,
   `characteristic`, `nps`, `njs`, `notes`, `seconds`, `length`).
5. The API cannot require a specific subset of difficulties and does not define what `minNps`/`maxNps` apply to, so
   those two checks run locally.

## Architecture

### Backend (`src/saber_tooth/beatsaver/`)

1. `client.py`: httpx client restricted to `https://api.beatsaver.com` for API calls and to BeatSaver's download hosts
   (taken from `versions[].downloadURL`, accepted only when the host is `r2cdn.beatsaver.com`, `cdn.beatsaver.com` or
   another `*.beatsaver.com` host over https). Descriptive `User-Agent: saber-tooth/<version>`, timeouts, a token
   bucket of at most 5 requests per second, and exponential backoff on 429/5xx honouring `Retry-After`.
2. `models.py`: typed dataclasses for the parts of MapDetail and Playlist we use; parsing tolerant of missing fields.
3. `cache.py`: SQLite tables `bs_maps` (id primary key, hash, json, fetched_at) and `bs_queries` (query key, page,
   ids, fetched_at); map details reused for 24 hours; query pages reused for 10 minutes.
4. `filters.py`: pure local filters:
   1. `difficulties`: set of required Standard difficulties, mode `all` (default) or `any`.
   2. `nps_range`: [min, max] inclusive with scope `any` (default, at least one Standard difficulty in range) or `all`.
   3. `characteristic`: default Standard.
   4. `min_rating` re-checked locally.
      Property tests cover them.
5. `search.py`: combines server and local filters. It sends everything BeatSaver supports (tags OR list, minRating,
   order, leaderboard, dates, bpm, duration, `fullSpread=true` when all five difficulties are required, and a loose
   `minNps`/`maxNps` widened to cover the local range), then scans BeatSaver pages (pageSize 100) applying local
   filters until it has `limit` matches or has scanned `max_pages` (default 10) pages. Returns matches, a `cursor`
   (next BeatSaver page plus offset) for infinite scroll, and `scanned` and `matched` counts so the UI can say how far
   it looked.
6. `download.py`: download job per map or per selection:
   1. Fetch the zip (size cap 100 MB, streamed to a temp file under DATA_DIR).
   2. Safe extraction: reject absolute paths, `..`, drive letters, symlinks; cap total uncompressed size (400 MB) and
      file count (500); extract into a `.partial` staging folder.
   3. Validate with `mapio.load_map` (vanilla rules apply; maps needing Noodle/Mapping Extensions are refused with a
      clear reason) and check the archive hash against the version hash when BeatSaver provides it.
   4. Skip when a library map with the same BeatSaver id or folder name already exists ("installed").
   5. Commit through `LevelsWriter` as `<key> (<songName> - <levelAuthorName>)` with illegal characters removed and
      the existing collision rule.
   6. Refresh the library; record `bs_id`, `bs_hash` on the library row so the BeatSaver view can show "Installed".
7. `playlists.py`: optional `.bplist` export of a selection (BeatSaber playlist JSON: `playlistTitle`,
   `playlistAuthor`, `songs: [{key, hash, songName}]`, optional base64 cover) into the game's `Playlists` folder,
   path from env `PLAYLISTS_DIR` (compose bind, optional; feature hidden when unset).

### API

1. `GET /api/beatsaver/search` with query params mirroring the filters (`q`, `tags` OR list, `min_rating`,
   `nps_min`, `nps_max`, `nps_scope`, `diffs`, `diffs_mode`, `ranked`, `order`, `ascending`, `from`, `to`,
   `bpm_min`, `bpm_max`, `duration_min`, `duration_max`, `cursor`, `limit`) -> `{items, cursor, scanned, matched}`;
   each item: id, name, song, mapper, cover_url, preview_url, bpm, duration, rating, upvotes, downvotes, tags,
   ranked, standard difficulties with nps/njs, installed (bool), library_id (or null).
2. `GET /api/beatsaver/maps/{id}`, `GET /api/beatsaver/playlists/search`, `GET /api/beatsaver/playlists/{id}`
   (with the same local filters applied to its maps).
3. `POST /api/beatsaver/download` body `{ids: [...]}` (max 100) -> `{"job": id}`; job result lists per-map outcome
   (installed, skipped with reason, failed with reason, folder).
4. `POST /api/beatsaver/playlist-export` body `{title, ids}` -> written path (only when PLAYLISTS_DIR is set).
5. Presets: `GET/POST/DELETE /api/beatsaver/presets` stored in SQLite; the "Gentle full-spread hits" preset from the
   requirements is seeded on first run.
6. All routes stay behind the host/origin middleware; MCP gets `beatsaver_search` and `beatsaver_download` tools.

### Frontend

1. Header switch (segmented control) Library | BeatSaver; route `/beatsaver` (query state in the URL) and
   `/beatsaver/playlists/:id`.
2. Same shell rules as the library: only the list scrolls, fixed and resizable columns, skeletons, mobile cards and
   mobile control bar.
3. Columns: Image, Title (song), Author (mapper), Levels (chips with NPS per difficulty on hover), Rating (percent
   with up/down counts), Length/BPM, Tags (compact chips), Status (Installed tick / downloading / failed), Actions
   (Download, Preview audio if `previewURL`, Open on BeatSaver).
4. Filter panel (popover in headers plus a "More filters" sheet): text, tags (multi with OR), rating minimum, NPS range
   with scope, required difficulties with any/all, ranked, date range, BPM and length ranges, order.
5. Presets bar: saved presets as chips; "Save current filters"; the seeded preset first.
6. Selection: checkboxes per row; "Download N" and "Export playlist" actions with a confirmation that lists counts
   and skips already installed maps; progress shown per row and as a job outcome.
7. Infinite scroll uses the API cursor; the footer shows "Scanned N BeatSaver maps, M match".
8. Playlists tab: search playlists, open one, the same table and filters over its maps, "Download all matching".

## Error handling

1. BeatSaver unreachable or rate limited: the view shows the error and a retry button; cached results stay visible.
2. Download failures are per map and never abort the rest of a batch.
3. Invalid or unsafe archives are refused with the reason; nothing reaches CustomLevels.

## Testing

1. BeatSaver responses come from recorded JSON fixtures served by `httpx.MockTransport`; no test calls the network.
2. Hypothesis properties for local filters and cursor paging (no duplicates, no gaps).
3. Zip safety tests: traversal, absolute paths, symlinks, size and count caps, corrupt archive, Noodle map refused.
4. API tests for every route including limits and 4xx paths; download job end to end into a temp levels dir.
5. Frontend Vitest tests for the view, presets, URL state, selection and download flows.

## Non-goals

1. Uploading maps, voting, BeatSaver accounts or authenticated endpoints.
2. A full offline mirror of BeatSaver.
