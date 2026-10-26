# .claude/agents

Project subagent definitions for Claude Code. Each file is Markdown with a front matter block (name, description, tools, model) and a short numbered procedure.

1. `map-auditor.md`: runs `task st:check -- <folder>` on one map folder and returns finding counts per rule. Read only.
2. `lightshow-learner.md`: runs `task st:learn -- <levels_dir> <out.json>` and returns template unit counts per environment.

Both agents only call project tasks and never write into the levels directory. See [architecture](../../docs/architecture.md) for the checks and the lightshow learner they wrap.
