# Jobs queue and Jobs tab design

Status: approved by the user on 2026-10-29 (chat design, eight points).

## Goal

1. Show at a glance what the server is working on, what waits, and what finished, so a stuck job is visible.
2. Keep every queued map operation across a container restart and run them one by one.
3. Keep job toasts across a page refresh.

## Current behaviour (2026-10-29, main 61f1a31)

1. `Jobs` (`src/saber_tooth/jobs.py`) wraps one `ThreadPoolExecutor(max_workers=1)` built in `api/core.py:80`; every kind (scan, fix, apply, crop, generate, learn, bs-download) shares it.
2. `submit` inserts a `queued` row in the `jobs` table, then hands a closure to the pool; the queue itself lives only in memory.
3. On startup `Store.fail_interrupted_jobs` marks every queued and running row failed, so a restart drops the whole queue.
4. Nothing stops two Fix jobs for the same map.
5. The API exposes only `GET /api/jobs/{id}`; no list.
6. Toasts live in the page (`useJobRunner`, `frontend/src/api/jobs.ts`); a refresh loses them.
7. `pollJob` gives up after 30 minutes (`MAX_JOB_MS`), counted from submit, so a job that waits long in the queue reports a client timeout while it is still queued.

## Design

### 1. Durable queue

1. The `jobs` table gains columns `args_json TEXT`, `started_at TEXT`, `progress TEXT`, `progress_at TEXT`, added through the existing missing-column migration list in `store.py`.
2. Each job kind has a named handler in a registry: `kind -> callable(**args) -> result`. `submit(kind, args, map_id)` stores `args_json` and wakes the worker; it no longer takes a closure.
3. Handlers: `scan(map_id)`, `fix(map_id)`, `apply(map_id)`, `crop(map_id, start, end, replace)`, `generate(source)` where source is a YouTube URL or an uploaded file path, `learn()`, `bs-download(ids)`.
4. One worker thread loops: claim the oldest `queued` row (atomic `UPDATE ... SET status='running', started_at=now WHERE id=(SELECT ... ORDER BY created_at, rowid LIMIT 1) AND status='queued'`), run its handler, write `done` or `failed`. It sleeps on a `threading.Event` that `submit` sets, with a 5 s fallback timeout.
5. Worker count stays 1; Fix and Generate are CPU heavy.
6. On startup only `running` rows become failed with the existing interrupted message; `queued` rows stay and the worker resumes them in order.
7. An uploaded-file generate job whose file is gone at run time fails with "the uploaded file is no longer available; upload it again". The handler removes the upload folder after the run, as today.
8. Unknown kind or unreadable `args_json` on a resumed row fails that job with a clear message; it never stops the worker.
9. `shutdown` stops the worker after the current job; it does not fail queued rows.

### 2. No duplicate map jobs

1. Submitting `scan`, `fix` or `apply` for a map that already has a `queued` or `running` job of the same kind returns that job's id instead of a new one.
2. Crop keeps its existing 409 when the map has any active job.

### 3. Cancel a queued job

1. `DELETE /api/jobs/{id}` on a `queued` job sets status `cancelled`; the worker skips it.
2. On a `running` job it returns 409 "a running job cannot be stopped"; on a finished job 409 "the job already finished"; unknown id 404.
3. Stopping a running Fix between rounds is out of scope.

### 4. Progress

1. Handlers may report progress through a callback the worker passes in; it writes `progress` and `progress_at`.
2. Fix reports `round N of M` at the start of each round (`fix_beatmap` loop, `service/fix.py:61`).
3. Other kinds report nothing; the UI shows elapsed time only.
4. Stale threshold: a running job with no progress (or no start, for kinds without progress) for 10 minutes shows a "no progress for X min" warning. Display only; nothing is killed.

### 5. `GET /api/jobs`

1. Response: `{"running": [job], "queued": [job], "recent": [job]}`.
2. `queued` is ordered oldest first; each has `position` (1 = next).
3. `recent` holds `done`, `failed` and `cancelled` jobs finished in the last 24 hours, newest first, at most 50.
4. Job fields: `id`, `kind`, `status`, `map_id`, `title` (map title from the library when `map_id` is set, else a kind label such as "Generate from YouTube"), `created_at`, `started_at`, `updated_at`, `progress`, `progress_at`, `error`.
5. `GET /api/jobs/{id}` keeps its shape and gains the same new fields.

### 6. Jobs tab

1. Third section tab "Jobs" next to Library and BeatSaver in `SectionTabs`, route `/jobs`, tip "What the server is working on."
2. The tab label carries a count of running plus queued jobs when above zero.
3. Page sections: Running (title, kind, elapsed, progress, stale warning), Queued (position, title, kind, waited time, Cancel), Recent (status icon, title, kind, duration, error text, finished time).
4. Titles link to the map page when `map_id` is set and the map still exists.
5. Polls `GET /api/jobs` every 2 s while anything is running or queued, every 10 s otherwise; stops while the tab is hidden.
6. Empty state: "Nothing running or queued."
7. Layout follows the library page styles; phone width stacks rows.

### 7. Toasts after refresh

1. On app load the app reads `GET /api/jobs` and restores a progress toast for each running or queued job, keyed exactly as `useJobRunner` keys it (`Fix:<map_id>`, `Scan:<map_id>`, and so on), and keeps polling each until it ends with the usual success or failure toast.
2. When more than 4 jobs are active, one summary toast "N running, M waiting" with a "Show jobs" action to `/jobs` replaces the per-job progress toasts; failure toasts still show one per job.
3. `pollJob`'s 30 minute limit counts from `started_at`, not from submit; a queued job shows "Queued, position P" instead of timing out.

### 8. Out of scope

1. A "fix selected" bulk action in the library.
2. A VR version of the Jobs tab.
3. An MCP tool that lists jobs.
4. Stopping a running job.

## Errors

1. Handler exception: job `failed` with the exception text, as today; `result` from the exception is kept.
2. Store error while marking a job: logged, worker continues with the next job.
3. List endpoint never fails on a missing map; the title falls back to the kind label.

## Testing

1. Store: migration adds the columns to an old database; claim takes oldest first and never the same row twice under two threads.
2. Worker: jobs run in submit order; a failing handler does not stop later jobs; cancel skips a queued job; progress is written.
3. Restart: queued rows survive `build_service` and run; running rows fail with the interrupted message.
4. Dedupe: second Fix for a busy map returns the same id; Fix on another map gets a new id.
5. Generate from a vanished upload fails with the stated message.
6. API: list shape, positions, 24 h and 50 limits, title fallback, cancel status codes.
7. Frontend: Jobs tab renders the three sections, cancel calls the API, polling slows when idle; toast rehydration restores keyed toasts after a remount; summary toast above 4 active; queued job does not time out.
8. No test runs a real Fix, generate or network call; handlers are stubbed.
