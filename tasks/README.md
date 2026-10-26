# tasks

1. `Taskfile.yml`: the `st:` task namespace, included by the root Taskfile.

Tasks:

1. `st:test`: run pytest (`task st:test -- <pytest args>`).
2. `st:check`, `st:inspect`: run the CLI on one map folder.
3. `st:survey`: read-only finding counts across a levels directory.
4. `st:learn`: build lightshow templates from installed maps.
5. `st:gen`: start a generation job from a URL.
6. `st:up`, `st:down`, `st:logs`: manage the docker compose stack.
7. `st:readme-check`: folder README coverage, see [scripts](../scripts/README.md).
8. `st:compose-check`: validate `docker-compose.yml`.

Run `task --list` for the current set. See [architecture](../docs/architecture.md).
