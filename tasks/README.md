# tasks

1. `Taskfile.yml`: the `st:` task namespace, included by the root Taskfile.

Tasks:

1. `st:test`: run pytest (`task st:test -- <pytest args>`).
2. `st:check`, `st:inspect`: run the CLI on one map folder.
3. `st:survey`: read-only finding counts across a levels directory.
4. `st:learn`: build lightshow templates from installed maps.
5. `st:gen`: start a generation job from a URL.
6. `st:up`, `st:stop`, `st:start`, `st:down`, `st:logs`: manage the docker compose stack; only `st:down` removes containers.
7. `st:readme-check`: folder README coverage, see [scripts](../scripts/README.md).
8. `st:compose-check`: validate `docker-compose.yml`.
9. `st:gate`, `st:review-diff`, `st:sync`: validation, review diffs and worktree state.
10. `st:lane`, `st:lane-list`, `st:lane-done`: parallel work lanes as git worktrees.
11. `st:commit`: format, stage and commit exactly the given paths.
12. `st:smoke`, `st:docker-health`, `st:browser-check`: read-only checks of the running stack; the last drives Chrome or Firefox headless.
13. `st:crepidoma-bump`: update the `.crepidoma` submodule and stage it.
14. `st:hub:check`, `st:hub:publish`: compare or publish the Docker Hub page; publish is run by a person.

The workflow tools are described in [workflow](../docs/workflow.md).

Run `task --list` for the current set. See [architecture](../docs/architecture.md).
