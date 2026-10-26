# 0006 Single-process FastAPI with SQLite

## Context

The service is for one user on localhost. Jobs are few and run for seconds to minutes. Non-goals include multi-user access, authentication and exposure beyond localhost.

## Decision

1. One Python 3.12 process runs FastAPI under uvicorn, an in-process job worker and the static frontend.
2. State lives in SQLite in the `saber-data` volume, in tables `maps`, `jobs` and `proposals`.
3. The port is published on `127.0.0.1` only.

## Consequences

1. Deployment is one container plus beat-analyser, with no broker or database server.
2. Jobs run inside the process, so a restart interrupts any job that is running.
3. Scaling beyond one user would need a queue and a different store.
