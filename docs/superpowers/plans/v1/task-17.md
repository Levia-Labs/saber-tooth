### Task 17: Frontend

**Skill:** `frontend-design:frontend-design` before writing.

**Files:**

- Create: `src/saber_tooth/web/index.html`, `web/app.js`, `web/timeline.js`, `web/style.css`
- Test: `tests/test_web.py` (served files reachable; `app.js` references only `/api/` routes that exist)

Views:

1. Library: table of maps (title, mapper, environment, errors, warnings), filter box, Scan button per row, Learn lightshows button.
2. Map detail: findings grouped by difficulty and rule; each proposal with summary, severity, Approve and Reject buttons, and a canvas timeline (`timeline.js`) showing the 4x3 grid lanes over the proposal's beat window, red and blue notes with cut arrows, before on the left and after on the right. "Approve all for this map" requires a confirm dialog. Apply button enabled when at least one proposal is approved; shows job progress and the result folder or conflict message.
3. New map: URL field and file upload, job progress, then the `create-map` proposal with per-difficulty note counts and a timeline of the first 16 bars of Expert; Approve writes the folder.

- [ ] **Steps:** test first, implement, run `uv run pytest tests/test_web.py -v`, then manual check through `task st:up` and the browser. Commit `feat: add review frontend`.
