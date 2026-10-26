# TODO

1. `quality:deep` needs `jscpd`, which is not installed. Install it or drop the duplicate-code step from the deep gate.
2. `.pre-commit-config.yaml` runs ruff with line length 100, while `pyproject.toml` sets 110. Align both to one value.
3. Info v4 and difficulty v4 BPM changes are ignored in v1. Add support.
