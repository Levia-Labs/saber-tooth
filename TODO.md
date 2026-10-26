# TODO

1. `quality:deep` duplication step reports "did not run": jscpd 5.4.2 (now installed) prints no "Total" line under `--silent`, which the shared task greps for (.crepidoma/taskfiles/quality/Taskfile.yml:53). Measured duplication is 4.99% (threshold 10). Fix upstream in Crepidoma.
2. Info v4 and difficulty v4 BPM changes (audio-data BPM) are ignored in v1. Read BPM from audio data and use it for timing.
3. `.claude/settings.json` is the verbatim Crepidoma template. An automated security review flagged broad allow rules (`Bash(task *)`, `git diff/log/show *` where a deny can be bypassed by long-option abbreviation, `pre-commit run *`, `git commit *` without a `--no-verify` deny) and the unpinned marketplace ref `main`. Fix upstream in Crepidoma, then resync.
4. The Crepidoma eslint hook template uses `npx --no eslint --config ...`, which npm 10+ breaks, and the shared `eslint.config.js` sets no browser globals, so the web code needs local overrides. Fix upstream in Crepidoma, then resync.
5. The generator places notes only. Add walls (decided: walls only, no bombs) on calm passages and build-ups for Hard and above.
6. On a Linux host the container user `app` has a fixed uid, so the `/levels` bind mount can be unwritable. Let the host uid be configured.

## 4 Fixer: swing-speed deletes whole swing; flip collapses mixed-cut swings; wide-jump multi-move loses candidates

status: open
class: quality

## 5 Frontend: finished Scan pulls view back; drawn canvases accumulate until resize; 4xx retried

status: open
class: quality

## 6 Origin check behind a TLS proxy needs X-Forwarded-Proto support if exposed beyond localhost

status: open
class: security
