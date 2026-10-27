# API

The service listens on `127.0.0.1:${SABER_PORT:-8100}`. There is no authentication; access is limited to localhost. Requests must carry a `Host` of `127.0.0.1`, `localhost` or `[::1]` (any port), or a name listed in the comma-separated environment variable `SABER_ALLOWED_HOSTS`; any other `Host` is refused with 403 to block DNS rebinding. Behind a TLS proxy, set `SABER_TRUSTED_PROXY_IPS` (comma list of single proxy addresses, no networks, empty by default). When the TCP peer is in that list, the `Origin` check uses the rightmost `X-Forwarded-Host` and `X-Forwarded-Proto` value, and both the direct `Host` and the forwarded host must be in the allowlist, so add the proxy upstream name to `SABER_ALLOWED_HOSTS`. The proxy must overwrite these headers rather than append (nginx: `proxy_set_header Host $host; proxy_set_header X-Forwarded-Host $host; proxy_set_header X-Forwarded-Proto $scheme;`). From any other peer those headers are ignored. The static frontend is served at `/`, and `GET /maps/{id}` and `GET /new` answer with `index.html` so deep links and reloads work. Any other `GET /api/...` path answers 404 JSON `{"error"}`. All other responses are JSON.

## Routes

1. `GET /api/health`: `{"status": "ok"}`. Cheap liveness probe used by the container HEALTHCHECK; it does not read the library, write the store or call the analyser, and it sits behind the same `Host` check as every other route. At startup the first library refresh runs in a background thread, so `/api/maps` and `/api/maps/facets` list only the maps indexed so far until it ends.
1. `GET /api/maps?offset=0&limit=40&sort=title&order=asc&q=&status=all&env=&q_fields=`: one page of the library, refreshed first if the set of folders under `/levels` changed. Answers `{"items", "total", "offset", "limit"}`; `total` counts every map matching `q`, `status` and `env`.
   1. `sort` is one of `title` (default), `mapper`, `environment`, `status`, `errors`, `warnings`, `scanned_at`, `bpm`, `duration`, `levels`. `bpm`, `duration` and `levels` put maps without a value last in both orders. `levels` sorts by the highest difficulty present, then by how many are present. `status` sorts unreadable, error, warn, scanning, applying, queued, unscanned, ok. `order` is `asc` or `desc`. Ties break by title, then id, so pages never overlap or skip.
   2. `q` is a case-insensitive substring of title, mapper, environment or folder (up to 200 characters). `q_fields` is a comma-separated list of `title` and `mapper` that restricts the text search to those fields (`q_fields=mapper` searches the mapper only). `status` filters to `all` (default) or a comma-separated list (also repeatable) of `error`, `warn`, `ok`, `unscanned`, `unreadable`, `scanning`, `applying`, `queued`. `env` is an exact environment name, repeatable or comma-separated (up to 50 names); a map matches any listed value. Environment names must not contain commas; the web app always repeats `env`. `mapper` is an exact mapper name, repeatable (up to 50 names of 200 characters; commas are part of the name); a map matches any listed value. `level` is `Easy`, `Normal`, `Hard`, `Expert` or `ExpertPlus`, repeatable or comma-separated; a map matches when it has any selected level, or every selected level with `level_mode=all` (`any` is the default).
   3. `limit` is 1 to 100, `offset` is 0 or more. Any bad value answers 400 `{"error"}`.
   4. Each item has `id`, `folder`, `title`, `mapper`, `environment`, `parse_error`, `errors`, `warnings`, `scanned_at`, `status`, `cover_url`, `difficulties`, `approved`, `pending`, `bpm`, `duration_s` and `job`. `bpm` is the Info.dat tempo; `duration_s` is the song length in seconds, from the Ogg audio file (sample rate and last granule position), else Info `audio.songDuration`, else the last note, bomb or wall converted with the tempo map; both are null when unknown. `job` is `{"id", "kind", "status"}` for the scan or apply job queued or running for the map, else null. `approved` counts approved proposals not yet applied; `pending` counts proposals awaiting a decision. `status` is `unreadable` (parse error), `scanning` or `applying` (a scan or apply job is running), `queued` (one is waiting), `unscanned` (never scanned), `error` (any error finding), `warn` (warnings only) or `ok` (scanned, no findings). Counts and `scanned_at` come from the last scan; `scanned_at` is null before one. `cover_url` is `/api/maps/{id}/cover` or null; `difficulties` lists the Standard difficulties in Info.dat.
   5. `GET /api/maps/facets`: `{"status": {<status>: n}, "environments": [{"name", "count"}], "mappers": [{"name", "count"}], "levels": {"Easy": n, "Normal": n, "Hard": n, "Expert": n, "ExpertPlus": n}, "total"}` over all maps, ignoring any filter. Environments and mappers sort by count descending, then name; maps with an empty mapper are not listed. Level counts are maps that have the level. Registered before `/api/maps/{id}`.
1. `GET /api/maps/{id}`: one item with the fields above, or 404.
1. `GET /api/maps/{id}/cover`: the cover image. The filename comes from Info.dat, must be a plain name ending `.png`, `.jpg` or `.jpeg`, must resolve to a regular file inside the map folder (no symlink out) and be at most 5 MB, else 404. Sends `Content-Type`, `Cache-Control: private, max-age=86400` and an `ETag` from modification time and size; `If-None-Match` answers 304.
1. `POST /api/maps/{id}/scan`: starts a `scan` job. Answers 409 if the map has a parse error.
1. `GET /api/maps/{id}/proposals`: proposals for a map or for a staged new map, with before and after excerpts. For a `create-map` proposal the excerpt shows the Expert notes of the staged map.
1. `POST /api/proposals/{id}/approve`: approve one proposal. Answers 409 for an applied proposal.
1. `POST /api/proposals/{id}/reject`: reject one proposal. Answers 409 for an applied proposal.
1. `POST /api/maps/{id}/approve-all`: approve every pending proposal for one map. Answers `{"approved": N}`.
1. `POST /api/maps/{id}/apply`: starts an `apply` job that writes the approved proposals into the sibling folder `<original name> [saber-tooth]`, or a numbered variant.
1. `POST /api/generate`: body `{"url": "<youtube url>"}` or a multipart audio file in the field `file`. Starts a `generate` job that ends in a `create-map` proposal.
1. `GET /api/lightshow`: `{"source", "environments", "units", "learned_at"}` for the active lightshow set. `source` is `learned` when `/data/lightshow.json` exists (written by the Learn button, which then overrides the bundled set) and `bundled` otherwise; `learned_at` is the file modification time as an ISO 8601 UTC string, or null for the bundled set.
1. `POST /api/lightshow/learn`: starts a `learn` job that learns from `/levels` and writes `/data/lightshow.json`, which replaces the bundled set from then on.
1. `GET /api/jobs/{id}`: `id`, `kind`, `status`, `error` and `result`.
1. BeatSaver routes, see [BeatSaver](#beatsaver).

Routes that start work answer `{"job": "<id>"}`. Poll the job until `status` is `done` or `failed`.

## Job results

1. `scan`: `{"map_id", "proposals", "analysis"}`. `proposals` is the number of proposals created, `analysis` is true when beat-analyser data was found for the map.
2. `apply`: `{"map_id", "folder"}`, the name of the folder written to `/levels`.
3. `generate`: `{"map_id", "proposal"}`. `map_id` is a staging id and `proposal` is the id of the `create-map` proposal.
4. `learn`: `{"units": N}`, the number of lightshow units indexed.
5. `bs-download`: `{"results": [{"id", "status", "reason", "folder"}]}` with `status` `installed`, `skipped` or `failed`.
6. A failed `apply` caused by conflicting proposals has `result` set to `{"conflict": [<proposal ids>]}` and the message in `error`.

## Errors

Errors answer `{"error": "<message>"}` with these codes.

1. 400: malformed body, missing `file`, or a URL that is not a YouTube URL.
2. 403: a `Host` outside the allowlist (any method), or a state-changing request whose `Origin` header does not match the scheme and host the client addressed (see above for proxies).
3. 404: unknown map, proposal or job. Ids that do not match their expected format are also 404.
4. 409: the map is unreadable, the proposal is already applied, or approved proposals conflict.
5. 413: the upload exceeds `MAX_UPLOAD_MB` (default 200).
6. 415: the uploaded file extension is not a supported audio type.

## BeatSaver

Search and download from BeatSaver. The server calls only `https://api.beatsaver.com` and `*.beatsaver.com` download hosts, at most 5 requests per second. Map details are cached 24 hours and query pages 10 minutes in `DATA_DIR/beatsaver.db`. Design: [spec](superpowers/specs/2026-10-27-beatsaver-integration-design.md).

1. `GET /api/beatsaver/search`: query keys `q` (200 characters), `tags` (comma list, matched as OR), `min_rating` (0 to 1), `min_upvotes` (integer, 0 to 1000000; sent to BeatSaver as `minUpVotes` and re-checked locally), `nps_min`, `nps_max` (0 to 30), `nps_scope` (`any` default or `all`), `diffs` (comma list of `Easy`, `Normal`, `Hard`, `Expert`, `ExpertPlus`), `diffs_mode` (`all` default or `any`), `ranked`, `order` (`Latest`, `Relevance`, `Rating` default, `Curated`, `Random`, `Duration`), `ascending`, `from`, `to` (`YYYY-MM-DD`), `bpm_min`, `bpm_max` (0 to 1000), `duration_min`, `duration_max` (seconds, 0 to 7200), `cursor`, `limit` (1 to 100, default 40). Difficulty and NPS filters apply to the Standard characteristic only and run locally. Answers `{"items", "cursor", "scanned", "matched"}`: `scanned` and `matched` count this response only, `cursor` is null at the end and advances even when no item matched. When BeatSaver rate limits mid-scan the response keeps what was found and adds `"partial": true` and `"retry_after"` (seconds).
   1. Item: `id`, `name`, `song`, `mapper`, `cover_url`, `preview_url` (https `*.beatsaver.com` or null), `bpm`, `duration` (seconds), `rating` (0 to 1), `upvotes`, `downvotes`, `tags`, `ranked`, `difficulties` (`[{"difficulty", "nps", "njs"}]`, Standard only), `installed`, `library_id` (library map id or null). A map is installed when a library row has its BeatSaver key or hash, or its folder starts with `<key> (`.
2. `GET /api/beatsaver/maps/{id}`: one item, 404 when unknown.
3. `GET /api/beatsaver/playlists/search?q=&cursor=`: `{"items": [{"id", "name", "owner", "cover_url", "map_count"}], "cursor"}`; the cursor is the next page number.
4. `GET /api/beatsaver/playlists/{id}`: the search response over the playlist's maps (same query keys and cursor) plus `"playlist"` (the playlist item).
5. `POST /api/beatsaver/download`: body `{"ids": [...]}`, 1 to 100 BeatSaver keys (413 above 100, 400 for malformed keys). Answers `{"job"}`; the job result is `{"results": [{"id", "status", "reason", "folder"}]}`. Archives are limited to 100 MB, 400 MB expanded and 500 entries, extracted without absolute paths, `..` or symlinks, validated with the map reader, refused when they require Noodle or Mapping Extensions, and written as a new folder `<key> (<song> - <mapper>)`. Maps already in the library are skipped. The archive hash is not verified against the BeatSaver hash.
6. `POST /api/beatsaver/playlist-export`: body `{"title", "ids"}` (up to 500 ids), writes `<title>.bplist` into `PLAYLISTS_DIR` without overwriting, answers `{"path"}`. 404 when `PLAYLISTS_DIR` is not set.
7. `GET /api/beatsaver/presets`: `[{"id", "name", "filters", "seeded"}]`, `filters` using the search query keys as strings. `POST /api/beatsaver/presets` with `{"name", "filters"}` answers the preset (400 invalid, 409 duplicate name or more than 100 presets); `DELETE /api/beatsaver/presets/{id}` answers `{"deleted"}` or 404. The preset "Gentle full-spread hits" is seeded once.
8. `GET /api/beatsaver/config`: `{"playlists_enabled"}`, true when `PLAYLISTS_DIR` points to an existing folder. Compose sets it from `PLAYLISTS_DIR_HOST`.

BeatSaver failures answer 404 (not found), 429 with `{"error", "retry_after"}` and a `Retry-After` header (rate limited and nothing found yet), or 502.

## URL rule

`POST /api/generate` accepts only `http` and `https` URLs whose host is exactly `youtube.com`, `www.youtube.com`, `m.youtube.com`, `music.youtube.com` or `youtu.be`. URLs with credentials, a malformed port, spaces, backslashes or non-printable characters are refused. See [ADR 0008](adr/0008-youtube-only-url-intake.md).

## Proposal states

1. `pending`: created by scan, waiting for a decision.
2. `approved`: accepted, not yet written.
3. `rejected`: declined, never written.
4. `applied`: written into the sibling folder.

## Upstream: beat-analyser

saber-tooth calls these beat-analyser routes server to server on the internal network.

1. `POST /upload`: multipart `file`.
2. `POST /download_yt`: JSON `{"url": "..."}`.
3. `GET /folders`: list project folders.
4. `GET /download/<name>`: download a project.

Project output is read from the shared volume instead; see [ADR 0005](adr/0005-beat-analyser-via-shared-volume.md).

## MCP

The same process serves a Model Context Protocol endpoint at `/mcp` (Streamable HTTP, stateless, JSON responses). It sits behind the same Host allowlist and same-origin check as the REST routes. See [ADR 0010](adr/0010-mcp-over-streamable-http-in-the-api-process.md).

Connect with `claude mcp add --transport http saber-tooth http://127.0.0.1:8100/mcp`. For another host name, add it to `SABER_ALLOWED_HOSTS`.

| Tool                         | Effect                                                                                                                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `list_maps(filter?)`         | Read-only. Up to 200 maps (item shape above) plus `total`; filter is a substring                                                                                                |
| `get_proposals(map_id)`      | Read-only. Up to 200 proposals plus `total`                                                                                                                                     |
| `scan_map(map_id)`           | Starts a scan job, returns `{"job"}`                                                                                                                                            |
| `job_status(job_id)`         | Read-only. Job status, error and result                                                                                                                                         |
| `approve_proposal(id)`       | Marks approved; idempotent; writes nothing                                                                                                                                      |
| `reject_proposal(id)`        | Marks rejected; idempotent; writes nothing                                                                                                                                      |
| `apply_map(map_id)`          | Starts an apply job; writes only a new folder in `CustomLevels`                                                                                                                 |
| `generate_from_youtube(url)` | Starts a generation job; same YouTube allowlist as `/api/generate`                                                                                                              |
| `learn_lightshows()`         | Starts a lightshow learning job                                                                                                                                                 |
| `beatsaver_search(...)`      | Read-only. BeatSaver search with `q`, `tags`, `min_rating`, `nps_min`, `nps_max`, `nps_scope`, `diffs`, `diffs_mode`, `cursor`, `limit`; same result as `/api/beatsaver/search` |
| `beatsaver_download(ids)`    | Starts a download job for up to 100 keys; writes only new folders in `CustomLevels`                                                                                             |

Failures come back as MCP tool errors with the REST message.
