# Workflow

How agents and humans work on this repo in parallel without overwriting each other. Every step is a task; arguments follow `--`.

## Lanes

1. One lane per concurrent job. `task st:lane -- <name>` creates `.worktrees/<name>` on branch `lane/<name>` from `main`, initialises `.crepidoma` and runs `npm ci` in `frontend/` when it exists.
2. Two agents in one working tree revert each other's uncommitted files during the pre-commit stash and restore. A lane has its own tree and index, so this cannot happen.
3. `task st:lane-list` shows each lane with ahead/behind against `main` and dirty counts.
4. Stay inside your lane directory. Never edit another lane or the main tree.

## Commit

1. `task st:commit -- -m "<message>" <paths...>` formats exactly those paths (ruff for Python, prettier for md, json, yaml, css, js, ts), stages them, appends the `Co-Authored-By` trailer once and commits.
2. If a hook rewrites files, the paths are staged again and the commit retried once. The helper then checks that HEAD carries the message and prints the short hash.
3. It never pushes and never skips hooks.

## Review

1. `task st:review-diff -- main..lane/<name>` writes the diff without lockfiles to `.cache/reviews/` and prints its size, files and commit count.
2. Read that file with ranges instead of pasting a diff into a message.

## Gate

1. `task st:gate` runs pytest, the Python, pre-commit and web linters, the frontend checks when `frontend/` exists, SAST, the quality gate, the README check and the compose check.
2. One line per gate: `name rc=N (Xs)`, then `gate: PASS|FAIL (k failed)`. Logs are in `.cache/gate/`; a failure prints the log path and the first error lines.
3. Narrow it with `--only a,b` or `--skip a,b`; add `--deep` for `quality:deep`; `--list` prints the gate names.

## Merge and finish

1. From the main tree: `git merge lane/<name>` after the gate passes in the lane.
2. `task st:lane-done CONFIRM=yes -- <name>` removes the worktree and branch. It refuses while the lane has uncommitted files or commits not in `main`.
3. `task st:sync [-- --fetch]` shows branch, upstream state, dirty counts and the `.crepidoma` commit for the main tree and every lane. Read-only.

## Running stack

1. `task st:smoke` waits for `/api/maps`, then checks the SPA routes and their assets, the maps API, facets, one cover, the MCP `tools/list` and compose health. Read-only.
2. `task st:docker-health` prints state and health per compose service, plus probe output and recent logs for any unhealthy or exited one.

## Crepidoma updates

1. `task st:crepidoma-bump [-- <ref>]` fetches the submodule, checks out the ref (default `origin/main`), prints the new commits, runs the lint and quality gates and stages the gitlink. Commit it with `task st:commit`.
