# .claude

Project Claude Code configuration for saber-tooth.

## Own contents

1. `settings.json`: models, permissions, hooks, enabled plugins. Tracked.
2. `settings.local.json`: per-machine overrides. Gitignored.
3. `agents/map-auditor.md`: runs the checks on one map folder and returns counts per rule.
4. `agents/lightshow-learner.md`: builds lightshow templates and reports unit counts per environment.
5. `agents/song-director.md`: researches a song, picks its environment and palette from `task st:environments`, and generates the map with that style.
6. `skills/README.md`, `skills/song-mood/SKILL.md`: the procedure song-director follows, from `task st:songmeta` to `task st:gen`.

## From the Crepidoma plugin

1. Plugin: `crepidoma@levia-labs`, user scope.
2. Hooks, generic agents, gates and skills come from the plugin and are not copied here.
3. Pillar files override plugin defaults of the same name; delete the override to fall back.
4. Plugin updates arrive through the marketplace; no local edits to plugin files.

## Rules

1. Folder name equals the skill `name` frontmatter; every `SKILL.md` carries a `description`.
2. Agent `tools:` lists only the tools the agent calls.
3. Add a skill, agent or command only when `CLAUDE.md` requires it.
