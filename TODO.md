# TODO

1. `quality:deep` needs `jscpd`, which is not installed. Install it or drop the duplicate-code step from the deep gate.
2. `.pre-commit-config.yaml` runs ruff with line length 100, while `pyproject.toml` sets 110. Align both to one value.
3. Info v4 and difficulty v4 BPM changes are ignored in v1. Add support.
4. `.claude/settings.json` is the verbatim Crepidoma template. An automated security review flagged broad allow rules (`Bash(task *)`, `git diff/log/show *` where a deny can be bypassed by long-option abbreviation, `pre-commit run *`, `git commit *` without a `--no-verify` deny) and the unpinned marketplace ref `main`. Fix upstream in Crepidoma, then resync.
5. Task 16 adds an `st:scan -- <map_id>` task, which the spec lists.
