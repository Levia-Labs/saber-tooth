# API

The service listens on `127.0.0.1:${SABER_PORT:-8100}`. There is no authentication; access is limited to localhost. Requests must carry a `Host` of `127.0.0.1`, `localhost` or `[::1]` (any port), or a name listed in the comma-separated environment variable `SABER_ALLOWED_HOSTS`; any other `Host` is refused with 403 to block DNS rebinding. Behind a TLS proxy, set `SABER_TRUSTED_PROXY_IPS` (comma list of single proxy addresses, no networks, empty by default). When the TCP peer is in that list, the `Origin` check uses the rightmost `X-Forwarded-Host` and `X-Forwarded-Proto` value, and both the direct `Host` and the forwarded host must be in the allowlist, so add the proxy upstream name to `SABER_ALLOWED_HOSTS`. The proxy must overwrite these headers rather than append (nginx: `proxy_set_header Host $host; proxy_set_header X-Forwarded-Host $host; proxy_set_header X-Forwarded-Proto $scheme;`). From any other peer those headers are ignored. The static frontend is served at `/`, and `GET /maps/{id}` and `GET /new` answer with `index.html` so deep links and reloads work. Any other `GET /api/...` path answers 404 JSON `{"error"}`. All other responses are JSON.

## Routes

1. `GET /api/maps?offset=0&limit=40&sort=title&order=asc&q=&status=all`: one page of the library, refreshed first if the set of folders under `/levels` changed. Answers `{"items", "total", "offset", "limit"}`; `total` counts every map matching `q` and `status`.
   1. `sort` is one of `title` (default), `mapper`, `environment`, `status`, `errors`, `warnings`, `scanned_at`. `status` sorts unreadable, error, warn, unscanned, ok. `order` is `asc` or `desc`. Ties break by title, then id, so pages never overlap or skip.
   2. `q` is a case-insensitive substring of title, mapper, environment or folder (up to 200 characters). `status` filters to `all` (default), `error`, `warn`, `ok`, `unscanned` or `unreadable`.
   3. `limit` is 1 to 100, `offset` is 0 or more. Any bad value answers 400 `{"error"}`.
   4. Each item has `id`, `folder`, `title`, `mapper`, `environment`, `parse_error`, `errors`, `warnings`, `scanned_at`, `status`, `cover_url`, `difficulties`, `approved` and `pending`. `approved` counts approved proposals not yet applied; `pending` counts proposals awaiting a decision. `status` is `unreadable` (parse error), `unscanned` (never scanned), `error` (any error finding), `warn` (warnings only) or `ok` (scanned, no findings). Counts and `scanned_at` come from the last scan; `scanned_at` is null before one. `cover_url` is `/api/maps/{id}/cover` or null; `difficulties` lists the Standard difficulties in Info.dat.
2. `GET /api/maps/{id}`: one item with the fields above, or 404.
3. `GET /api/maps/{id}/cover`: the cover image. The filename comes from Info.dat, must be a plain name ending `.png`, `.jpg` or `.jpeg`, must resolve to a regular file inside the map folder (no symlink out) and be at most 5 MB, else 404. Sends `Content-Type`, `Cache-Control: private, max-age=86400` and an `ETag` from modification time and size; `If-None-Match` answers 304.
4. `POST /api/maps/{id}/scan`: starts a `scan` job. Answers 409 if the map has a parse error.
5. `GET /api/maps/{id}/proposals`: proposals for a map or for a staged new map, with before and after excerpts. For a `create-map` proposal the excerpt shows the Expert notes of the staged map.
6. `POST /api/proposals/{id}/approve`: approve one proposal. Answers 409 for an applied proposal.
7. `POST /api/proposals/{id}/reject`: reject one proposal. Answers 409 for an applied proposal.
8. `POST /api/maps/{id}/approve-all`: approve every pending proposal for one map. Answers `{"approved": N}`.
9. `POST /api/maps/{id}/apply`: starts an `apply` job that writes the approved proposals into the sibling folder `<original name> [saber-tooth]`, or a numbered variant.
10. `POST /api/generate`: body `{"url": "<youtube url>"}` or a multipart audio file in the field `file`. Starts a `generate` job that ends in a `create-map` proposal.
11. `POST /api/lightshow/learn`: starts a `learn` job that rebuilds the lightshow template index.
12. `GET /api/jobs/{id}`: `id`, `kind`, `status`, `error` and `result`.

Routes that start work answer `{"job": "<id>"}`. Poll the job until `status` is `done` or `failed`.

## Job results

1. `scan`: `{"map_id", "proposals", "analysis"}`. `proposals` is the number of proposals created, `analysis` is true when beat-analyser data was found for the map.
2. `apply`: `{"map_id", "folder"}`, the name of the folder written to `/levels`.
3. `generate`: `{"map_id", "proposal"}`. `map_id` is a staging id and `proposal` is the id of the `create-map` proposal.
4. `learn`: `{"units": N}`, the number of lightshow units indexed.
5. A failed `apply` caused by conflicting proposals has `result` set to `{"conflict": [<proposal ids>]}` and the message in `error`.

## Errors

Errors answer `{"error": "<message>"}` with these codes.

1. 400: malformed body, missing `file`, or a URL that is not a YouTube URL.
2. 403: a `Host` outside the allowlist (any method), or a state-changing request whose `Origin` header does not match the scheme and host the client addressed (see above for proxies).
3. 404: unknown map, proposal or job. Ids that do not match their expected format are also 404.
4. 409: the map is unreadable, the proposal is already applied, or approved proposals conflict.
5. 413: the upload exceeds `MAX_UPLOAD_MB` (default 200).
6. 415: the uploaded file extension is not a supported audio type.

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

| Tool                         | Effect                                                                           |
| ---------------------------- | -------------------------------------------------------------------------------- |
| `list_maps(filter?)`         | Read-only. Up to 200 maps (item shape above) plus `total`; filter is a substring |
| `get_proposals(map_id)`      | Read-only. Up to 200 proposals plus `total`                                      |
| `scan_map(map_id)`           | Starts a scan job, returns `{"job"}`                                             |
| `job_status(job_id)`         | Read-only. Job status, error and result                                          |
| `approve_proposal(id)`       | Marks approved; idempotent; writes nothing                                       |
| `reject_proposal(id)`        | Marks rejected; idempotent; writes nothing                                       |
| `apply_map(map_id)`          | Starts an apply job; writes only a new folder in `CustomLevels`                  |
| `generate_from_youtube(url)` | Starts a generation job; same YouTube allowlist as `/api/generate`               |
| `learn_lightshows()`         | Starts a lightshow learning job                                                  |

Failures come back as MCP tool errors with the REST message.
