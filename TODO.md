# TODO

1. `quality:deep` duplication step reports "did not run": jscpd 5.4.2 (now installed) prints no "Total" line under `--silent`, which the shared task greps for (.crepidoma/taskfiles/quality/Taskfile.yml:53). Measured duplication is 4.99% (threshold 10). Fix upstream in Crepidoma.
2. Info v4 and difficulty v4 BPM changes (audio-data BPM) are ignored in v1. Read BPM from audio data and use it for timing.
3. `.claude/settings.json` is the verbatim Crepidoma template. An automated security review flagged broad allow rules (`Bash(task *)`, `git diff/log/show *` where a deny can be bypassed by long-option abbreviation, `pre-commit run *`, `git commit *` without a `--no-verify` deny) and the unpinned marketplace ref `main`. Fix upstream in Crepidoma, then resync.
4. The Crepidoma eslint hook template uses `npx --no eslint --config ...`, which npm 10+ breaks, and the shared `eslint.config.js` sets no browser globals, so the web code needs local overrides. Fix upstream in Crepidoma, then resync.
5. Walls follow-ups: window regeneration (empty-gap fills) emits and preserves no walls; flat-energy songs get no walls; proposal views show only the deleted wall (no surrounding wall context).
6. The bandit step of `quality:deep` scans the `.crepidoma` submodule (66 findings) and its baseline is a bare count, so new findings in own code are hard to spot. Exclude vendored code and record per-finding baselines. Fix upstream in Crepidoma.
