# api

Everything that talks to the HTTP API; field names live here only.

1. `types.ts`: response shapes and status keys.
2. `client.ts`: typed request functions; the only module that calls `fetch`.
3. `queries.ts`: TanStack Query hooks, cache patching and live polling of running rows.
4. `jobs.ts`: start a job and poll it to the end, with backoff and retry rules.
5. `beatsaver.ts`: BeatSaver response types, request functions and query hooks (the /api/beatsaver contract).
