# api

Everything that talks to the HTTP API; field names live here only.

1. `types.ts`: response shapes and status keys.
2. `client.ts`: typed request functions; the only module that calls `fetch`.
3. `queries.ts`: TanStack Query hooks, cache patching and live polling of running rows; `useTimeline` loads the crop timeline.
4. `jobs.ts`: start a job and poll it to the end with backoff and retry rules; it never gives up while the server reports the job queued or running; `useJobRunner` toasts are one-row, show rounds and open the Jobs page on click; `watchedJobs` lists the ids a live poll owns.
5. `beatsaver.ts`: BeatSaver response types, request functions and query hooks (the /api/beatsaver contract).
6. `fix.ts`: the one-click Fix: starts the job, follows it and keeps its outcomes for the alerts.
7. `generate.ts`: `useGenerate`, the one-step generate job: keyed progress, success and failure toasts, then opens the new map.
8. `joblist.ts`: the shared job list query, polling 2 s while jobs are active and 10 s when idle.
