# TODO

1. `quality:deep` needs `jscpd`, which is not installed. Install it or drop the duplicate-code step from the deep gate.
2. `.pre-commit-config.yaml` runs ruff with line length 100, while `pyproject.toml` sets 110. Align both to one value.
3. Info v4 and difficulty v4 BPM changes are ignored in v1. Add support.
4. `.claude/settings.json` is the verbatim Crepidoma template. An automated security review flagged broad allow rules (`Bash(task *)`, `git diff/log/show *` where a deny can be bypassed by long-option abbreviation, `pre-commit run *`, `git commit *` without a `--no-verify` deny) and the unpinned marketplace ref `main`. Fix upstream in Crepidoma, then resync.
5. Task 16 adds an `st:scan -- <map_id>` task, which the spec lists.
6. The Crepidoma eslint hook template uses `npx --no eslint --config ...`, which npm 10+ breaks, and the shared `eslint.config.js` sets no browser globals. Fix upstream in Crepidoma, then resync.
7. Info v4 and difficulty v4 audio-data BPM is ignored in v1. Read BPM from audio data and use it for timing.
8. Only the Standard characteristic is read and written. Other characteristics (OneSaber, NoArrows, 360Degree, 90Degree, Lawless, Lightshow) are ignored. Add support.
9. The generator places notes only. It emits no bombs and no walls. Add both.
10. The timeline JavaScript has no unit tests. Add tests with `node --test`.
11. The Crepidoma shared `eslint.config.js` defines no browser globals, so the web code needs local overrides. Fix upstream in Crepidoma, then resync.
12. On a Linux host the container user `app` has a fixed uid, so the `/levels` bind mount can be unwritable. Let the host uid be configured.

## 1 Apply race: rejection between unchanged() and write_fixed still writes the change (service/core.py)

status: open
class: bug

## 2 Burst-slider tail match in fixer/sliders.py _at can hit an unrelated same b/x/y/c note

status: open
class: bug

## 3 Tempo map never steers beat 1; noisy first interval can leave >10 ms error (generator/tempo.py)

status: open
class: quality

## 4 Fixer: swing-speed deletes whole swing; flip collapses mixed-cut swings; wide-jump multi-move loses candidates

status: open
class: quality

## 5 Frontend: finished Scan pulls view back; drawn canvases accumulate until resize; 4xx retried

status: open
class: quality

## 6 Origin check behind a TLS proxy needs X-Forwarded-Proto support if exposed beyond localhost

status: open
class: security
