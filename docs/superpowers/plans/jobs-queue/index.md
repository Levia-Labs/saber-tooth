# Jobs Queue and Jobs Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A durable SQLite-backed job queue drained by one worker thread, a `GET /api/jobs` list and cancel endpoint, a Jobs tab next to Library and BeatSaver, and job toasts that survive a page refresh.

**Architecture:** Job rows already live in the `jobs` table; they gain their arguments, start time and progress, and a single worker thread claims the oldest queued row and runs a named handler for its kind, so queued work survives a restart. The API lists running, queued and recent jobs with map titles; the frontend reads that list through one React Query hook shared by the Jobs page, the tab count and an app-wide toast watcher that restores toasts for jobs no live page is watching.

**Tech Stack:** Python 3.12, FastAPI, SQLite, pytest, hypothesis; React, React Router, TanStack Query, Vitest, Testing Library.

**Spec:** `docs/superpowers/specs/2026-10-29-jobs-queue-design.md`

## Global Constraints

1. Worker count stays 1.
2. Stale threshold: 10 minutes without progress (or since start, for kinds without progress).
3. `recent`: `done`, `failed`, `cancelled` jobs updated in the last 24 hours, newest first, at most 50.
4. Polling: every 2 s while anything is running or queued, every 10 s otherwise, paused while the tab is hidden.
5. More than 4 active jobs fold into one summary toast "N running, M waiting" with a "Show jobs" action to `/jobs`.
6. Exact messages: "the uploaded file is no longer available; upload it again", "a running job cannot be stopped", "the job already finished", "Nothing running or queued.", tab tip "What the server is working on."
7. `pollJob`'s 30 minute limit counts from the moment the job is seen running, never while queued.
8. Source files stay at or under 300 lines; text I/O passes `encoding="utf-8"`; no em dashes; every folder README lists its files.
9. Commits from the main thread only, with `task st:commit -- -m "<message>" <paths>`; implementers do not commit.
10. Tests never run a real Fix, generate or network call; handlers are stubbed.

## Review Focus

1. A map deleted while its Fix waits in the queue: the job fails with the map-not-found message, the list still shows it with the stored title fallback, and the worker continues. Test in Task 3.
2. Cancel racing the worker's claim: exactly one wins; a cancelled job never runs and a claimed job is never reported cancelled. Test in Task 1.
3. A forged or stale `upload` argument pointing outside `DATA_DIR/uploads`: the generate handler refuses it with the upload-gone message and deletes nothing. Property test in Task 3.
4. Existing frontend tests whose fetch stub answers unknown paths with `{}`: the toast watcher and tab count treat that as an empty list and never toast or throw. Test in Task 5.
5. A page that started a job unmounts (navigating away from the map page): the watcher takes the job over with the same toast key, no duplicate toast, and shows its finish. Test in Task 7.

## File Map

1. Create `src/saber_tooth/store_jobs.py`: `JobRows` mixin, every SQL statement on the `jobs` table.
2. Modify `src/saber_tooth/store.py`: schema columns, migrations, index, `Store` gains the mixin; job methods move out.
3. Modify `src/saber_tooth/store_claims.py`: `fail_interrupted_jobs` and `INTERRUPTED` move to `store_jobs.py`.
4. Rewrite `src/saber_tooth/jobs.py`: worker thread, handler registry.
5. Create `src/saber_tooth/api/jobs_api.py`: core handlers, job views, list and cancel.
6. Modify `src/saber_tooth/api/core.py`, `api/crop_api.py`, `api/beatsaver.py`, `api/__init__.py`, `service/fix.py`.
7. Frontend: modify `src/api/types.ts`, `src/api/client.ts`, `src/api/jobs.ts`, `src/api/queries.ts`, `src/components/SectionTabs.tsx`, `src/App.tsx`; create `src/api/joblist.ts`, `src/lib/jobtime.ts`, `src/lib/jobtoasts.ts`, `src/pages/JobsPage.tsx`, `src/components/JobToasts.tsx`, `src/styles/jobs.css`.
8. READMEs of every touched folder.

## Tasks

1. [Task 1: Durable job rows in the store](task-01a.md) (continues in [task-01b.md](task-01b.md))
2. [Task 2: One worker thread drains the queue](task-02.md)
3. [Task 3: Handlers for every job kind and Fix round progress](task-03.md)
4. [Task 4: `GET /api/jobs`, job detail fields and cancel](task-04.md)
5. [Task 5: Frontend job data layer](task-05.md)
6. [Task 6: Jobs tab and page](task-06.md)
7. [Task 7: Toasts that survive refresh and navigation](task-07a.md) (continues in [task-07b.md](task-07b.md))
8. [Task 8: Docs, build and full gate](task-08.md)
