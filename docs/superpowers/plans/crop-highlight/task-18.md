# Task 18: Docs

**Files:**

- Create: `src/saber_tooth/crop/README.md`
- Modify: `docs/api.md`
- Modify: `docs/architecture.md`
- Modify: `src/saber_tooth/README.md`
- Modify: `src/saber_tooth/service/README.md`
- Modify: `src/saber_tooth/api/README.md`
- Modify: `tests/README.md`
- Modify: `frontend/src/components/README.md`
- Modify: `frontend/src/lib/README.md`
- Modify: `frontend/src/api/README.md`
- Modify: `frontend/src/styles/README.md`
- Modify: `frontend/tests/README.md`

**Interfaces:**

Consumes: the names and routes of Tasks 1 to 16. Produces: documentation only. Every edit below is an anchored addition; several of these files carry another lane's uncommitted edits, so do not rewrite or reformat them.

- [ ] **Step 1: Create the package README**

Create `src/saber_tooth/crop/README.md`:

```markdown
# crop

Crops a map to a 1 or 2 minute highlight on song-part boundaries. Design: [spec](../../../docs/superpowers/specs/2026-10-28-crop-highlight-design.md). Routes: [api.md](../../../docs/api.md).

1. `errors.py`: `CropError`, `NoNotes`, `InvalidWindow`.
2. `phrases.py`: the bar and phrase grid, the tempo at a beat, the hardest difficulty with notes, and the drift of the grid against analyser beats.
3. `nps.py`: notes per second per difficulty (bombs excluded, a chain counted once), and the mean and slope over a span.
4. `sections.py`: change scores per phrase start and the section boundaries above the 70th percentile.
5. `window.py`: the length band, allowed ends by kind, the window score and the suggestions.
6. `timeline.py`: builds the timeline of one map, resolves a requested window and gives the JSON of `GET /api/maps/{id}/timeline`.
7. `shift.py`: pure crop of a `Beatmap`: shift, trim, 2 s lead-in, light fade-in and blackout.
8. `info.py`: Info.dat song name suffix and preview start.
9. `write.py`: the ffmpeg cut and the new folder through `LevelsWriter`.

Test with `uv run pytest tests/test_crop_*.py -q`.
```

- [ ] **Step 2: Edit `docs/api.md`**

1. Replace the line

```
1. `POST /api/maps/{id}/scan`: starts a `scan` job. Answers 409 if the map has a parse error.
```

with

```
1. `POST /api/maps/{id}/scan`: starts a `scan` job. Answers 409 if the map has a parse error.
1. `GET /api/maps/{id}/timeline`: the crop timeline `{"map_id", "duration_s", "bpm", "hardest", "map_only", "grid_drift_s", "nps", "sections", "lengths"}`. `nps` maps each difficulty that has notes to notes per second in 1 s steps (bombs excluded, a chain counts once). `sections` lists `{"start_beat", "end_beat", "start_s", "end_s", "nps", "intensity"}`. `lengths` has the keys `"60"` and `"120"`, each `{"enabled", "reason", "band", "suggestions", "starts"}`: `band` is `[54, 66]` or `[108, 132]` seconds, `suggestions` is the best window then the next two (`{"start_beat", "end_beat", "start_s", "end_s", "length_s", "end_kind", "score"}`), `starts` is every allowed start with its allowed `ends` (`{"beat", "seconds", "kind"}`, kind `section`, `phrase`, `bar4` or `bar`). `map_only` is true when the map was never scanned with analysis. Times are given in beats and seconds. 404 for an unknown map, 409 for an unreadable map, 422 with the reason when no Standard difficulty has notes or the song length is unknown.
1. `POST /api/maps/{id}/crop`: body `{"start_beat", "end_beat"}`. Starts a `crop` job that writes a new `<map> [1 min]` or `<map> [2 min]` folder beside the original (a taken name gets a number); the original is never changed. 422 names the broken rule (not a number, end not after start, start not a section boundary, length outside both bands, end not an allowed end point), 409 while the map has a queued or running job or is unreadable, 400 for a body that is not JSON.
```

2. Replace the line

```
6. A failed `apply` caused by conflicting proposals has `result` set to `{"conflict": [<proposal ids>]}` and the message in `error`.
```

with:

```
6. `crop`: `{"map_id", "folder", "cropped_id", "label", "start_beat", "end_beat", "length_s"}`: the new folder, its map id, `1 min` or `2 min`, the chosen beats and the length in seconds.
7. A failed `apply` caused by conflicting proposals has `result` set to `{"conflict": [<proposal ids>]}` and the message in `error`.
```

3. In the Errors list add after the 409 item:

```
5. 422: a crop request whose `start_beat` or `end_beat` breaks a window rule, or a timeline that cannot be built; the message names the rule.
```

and renumber the 413 and 415 items to 6 and 7.

4. In the MCP table insert these rows directly above the row that starts with ``| `beatsaver_search(...)` ``:

```
| `map_timeline(map_id)`       | Read-only. The timeline of `GET /api/maps/{id}/timeline`: NPS per difficulty, sections and the 1 and 2 minute windows with every allowed start and end                          |
| `crop_map(map_id, ...)`      | Starts a crop job from `start_beat` and `end_beat` of `map_timeline`; writes only a new folder in `CustomLevels`, never edits the map                                            |
```

Then run `npx --prefix frontend prettier --config .crepidoma/configs/.prettierrc --check docs/api.md`. If it reports only table alignment, run it with `--write` and confirm `git diff --stat docs/api.md` shows no changes beyond the lines above and table whitespace.

- [ ] **Step 3: Edit `docs/architecture.md`**

1. Change `Larger parts are packages: \`mapio\`, \`checks\`, \`generator\`, \`fixer\`, \`lightshow\`, \`service\`, \`api\` and \`web\`.`to`Larger parts are packages: \`mapio\`, \`checks\`, \`generator\`, \`fixer\`, \`lightshow\`, \`service\`, \`crop\`, \`api\` and \`web\`.`.
2. After the end of item 11 (the text ending `while \`index.html\` is \`no-cache\`.`) add:

```
12. `crop`: turns a map into a 1 or 2 minute highlight. `phrases` builds the bar and phrase grid from the tempo grid; `nps` counts notes per second per difficulty; `sections` scores each phrase start by how much drums, bass and chords, melody, lights and note density change across it and keeps scores above the 70th percentile as section boundaries (only the two map terms, flagged `map_only`, without analysis); `window` takes starts on boundaries and ends inside a 10 percent band, ranked by 0.7 times the mean NPS plus 0.3 times a build-up bonus minus 0.1 when the end is not a section boundary; `shift` crops the map with a 2 s lead-in and light fades; `write` writes `<map> [1 min]` or `[2 min]` with an ffmpeg-cut song through `LevelsWriter`. The timeline uses the analysis stored by the last scan and never calls the analyser. The map page offers the panel as a disclosure and fetches the timeline only when it is opened. Design: [spec](superpowers/specs/2026-10-28-crop-highlight-design.md).
```

- [ ] **Step 4: Edit the READMEs**

1. `src/saber_tooth/README.md`: after the line starting `7. [web/](web/README.md)` add `8. [crop/](crop/README.md): crop a map to a 1 or 2 minute highlight.`; change `3. \`analysis.py\`, \`analyser_client.py\`, \`audio.py\`: beat-analyser output, its HTTP client and audio conversion.`to end`its HTTP client, audio conversion and cutting.`.
2. `src/saber_tooth/service/README.md`: after the line ending `and its rows from the store.` add `8. \`crop.py\`: \`crop_timeline\`, \`crop_check\` and \`crop_map\`, the timeline and job body of the crop highlight, attached to \`Service\` the way \`fix_map\` is.`.
3. `src/saber_tooth/api/README.md`: after the line ending `adds \`beatsaver_search\` and \`beatsaver_download\`.`add`9. \`crop_api.py\`, \`crop_routes.py\`: the crop timeline and crop job (see [api.md](../../../docs/api.md)); \`mcp_tools.py\` adds \`map_timeline\` and \`crop_map\`.`.
4. `tests/README.md`: change `\`test_safe_fs\`, \`test_delete_map\`.`to`\`test_safe_fs\`, \`test_delete_map\`, \`test_crop_*\` (with the synthetic maps of \`crop_helpers.py\`), \`test_audio_cut\`, \`test_analysis_pitched\`, \`test_api_crop\`.`.
5. `frontend/src/components/README.md`: add `13. \`CropPanel.tsx\`, \`NpsChart.tsx\`: the collapsed Crop panel on the map page and its SVG chart of notes per second with draggable, keyboard-steppable window edges.`.
6. `frontend/src/lib/README.md`: add `12. \`crop.ts\`: snapping, stepping and re-picking the crop window edges, and the \`m:ss.s\` clock.`.
7. `frontend/src/api/README.md`: change the `queries.ts` item to end `and live polling of running rows; \`useTimeline\` loads the crop timeline.`.
8. `frontend/src/styles/README.md`: add `10. \`crop.css\`: the crop panel and its NPS chart.`.
9. `frontend/tests/README.md`: add `10. \`crophelpers.tsx\`, \`croplib.test.ts\`, \`cropchart.test.tsx\`, \`croppanel.test.tsx\`, \`cropwiring.test.tsx\`: the crop timeline fixture and API stub, snapping helpers, the SVG chart, the panel states and its place on the map page.`.

- [ ] **Step 5: Check the docs**

Run: `git add src/saber_tooth/crop/README.md && uv run python scripts/readme_check.py`
Expected: `missing=0`.
Run: `uv run pytest tests/test_readme_check.py -q`
Expected: pass.
Run: `uv run python -c "import sys; print([p for p in sys.argv[1:] if chr(0x2014) in open(p, encoding='utf-8').read()])" docs/api.md docs/architecture.md src/saber_tooth/crop/README.md`
Expected: `[]` (no em dash was added).

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "docs: crop highlight routes, tools, package and tests"` (subagents never commit).

---
