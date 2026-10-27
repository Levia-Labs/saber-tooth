# scripts

Standalone helper scripts run through the task runner.

1. `readme_check.py`: checks that every tracked project folder has a README.md. Run `task st:readme-check` to list missing folders (exit 1 if any) or `task st:readme-check -- --list` to list every folder that needs one. Tested by `tests/test_readme_check.py`.
2. `gate.py`: runs every validation gate with one result line each. `task st:gate [-- --only a,b --skip a,b --deep --list]`. Logs go to `.cache/gate/<name>.log`; a failure prints the log path and up to 3 lines.
3. `review_diff.py`: writes `git diff <range>` without lockfiles to `.cache/reviews`. `task st:review-diff -- <range> [--out DIR] [--exclude GLOB]`.
4. `sync.py`: one line per worktree with branch, ahead/behind, dirty and untracked counts and the `.crepidoma` commit. `task st:sync [-- --fetch]`. Read-only.
5. `smoke.py`: checks a running stack (SPA routes, assets, maps API, facets, cover, MCP, compose health). `task st:smoke [-- --base URL --timeout S]`. Read-only.
6. `lane.py`: work lanes as worktrees. `task st:lane -- <name> [--base main]`, `task st:lane-list`, `task st:lane-done CONFIRM=yes -- <name>`; done refuses unless the lane is clean and merged into main.
7. `commit.py`: formats, stages and commits exactly the named paths with the Co-Authored-By trailer, retrying once after a hook rewrite. `task st:commit -- -m "<message>" <paths...>`. Never pushes, never skips hooks.
8. `crepidoma_bump.py`: fetches and checks out a `.crepidoma` ref, prints the log, runs the lint and quality gates and stages the gitlink. `task st:crepidoma-bump [-- <ref>]`. Never commits.
9. `docker_health.py`: state, health, probe output and recent logs per compose service. `task st:docker-health`. Read-only.

10. `learn_bundle.py`: regenerates the bundled lightshow set from a levels directory with a fixed gzip header, so equal input gives equal bytes; prints environments, units and size. `task st:learn-bundle -- <levels_dir> [--out PATH]`.

Each script has `-h`. Tests are `tests/test_script_*.py`; they use fakes or temporary git repositories and never touch Docker or the network. See [workflow](../docs/workflow.md).

Tasks are defined in [tasks/Taskfile.yml](../tasks/README.md).
