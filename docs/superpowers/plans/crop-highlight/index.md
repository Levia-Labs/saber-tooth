# Crop Highlight Implementation Plan (index)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn any map into a 1 or 2 minute highlight: the most intense stretch by notes per second, opening on a build-up, both cut points on song-part boundaries, written as a new playable folder beside the original.

**Architecture:** A pure backend package `src/saber_tooth/crop/` (grid, NPS, sections, window search, shift and trim, Info fields, folder write, timeline assembly) behind two `Service` functions (`crop_timeline`, `crop_map`) attached the way `fix_map` is. A `CropApi` class and `crop_routes.py` expose `GET /api/maps/{id}/timeline` and `POST /api/maps/{id}/crop`; two MCP tools wrap the same calls. The React map page gains a collapsed Crop panel with a hand-written SVG NPS chart, snapping handles and keyboard control.

**Tech Stack:** Python 3.12, uv, FastAPI, SQLite, pytest, hypothesis, ruff; ffmpeg through `subprocess`; React 19, TypeScript, TanStack Query, vitest, Testing Library.

**Spec:** `docs/superpowers/specs/2026-10-28-crop-highlight-design.md`

## Global Constraints

Values copied from the spec; tests pin them, code must not change them.

1. Band: target length plus or minus 10 percent. 1 min is 54 to 66 s, 2 min is 108 to 132 s. Targets are 60 and 120 s only.
2. Bar: 4 beats on the map's tempo grid. Phrase: 8 bars counted from the first downbeat that carries notes. Section: a run of phrases between two boundaries, at least 8 bars long.
3. Section boundary: a phrase-start change score above the song's 70th percentile; boundaries closer than 8 bars keep the higher score; without analysis only the map terms count and the result is flagged `map_only`.
4. Change score terms (each normalised, summed): drum onset rate, bass and chord note rate, melody note rate and pitch range, light events per bar, note density.
5. NPS: 1 s steps per difficulty, bombs excluded, a chain counted as one note.
6. Window: start is always a section boundary. End, first match inside the band: section boundary, else phrase start, else 4-bar line, else bar line (kinds `section`, `phrase`, `bar4`, `bar`).
7. Score per start: 0.7 times the mean NPS of the hardest difficulty over the window, plus 0.3 times the build-up bonus, minus 0.1 when the end is not a section boundary. NPS terms are normalised to the song's peak. Output: best window, next two, every start, per start the allowed ends with kind.
8. Audio: ffmpeg cut, 0.5 s fade-in, fade-out over the last bar. First note at 2 s or later (lead-in).
9. Notes, arcs and chains crossing a cut edge are dropped; walls are trimmed; BPM changes inside the window are kept and re-timed; lights fade in at the start and black out at the end; Info.dat gets the song name suffix and a preview start inside the new audio.
10. Output folder `<original> [1 min]` or `<original> [2 min]` through `LevelsWriter`; a taken name gets a numbered name, never an overwrite; the original is never changed; Fix is not run on the copy.
11. API: `GET /api/maps/{id}/timeline`; `POST /api/maps/{id}/crop` with `{start_beat, end_beat}` answers 422 naming the broken rule, else `{job}` of kind `crop`. MCP: `map_timeline` and `crop_map` only. No MCP tool deletes, overwrites or edits a map.
12. Frontend: snapping to allowed points only, arrow keys step to the next or previous allowed point, Shift+arrow jumps a section, amber readout when the end is not a section boundary, Create disabled while a job runs on the map.
13. Repo rules: Python 3.12 and uv; every file at most 300 lines (`service/core.py` is at 300 and `api/core.py` at 287, so all new logic lives in new modules); `encoding="utf-8"` on every text read and write; numbered lists in docs; no em dashes anywhere; tests never touch real user data (tmp folders and synthetic maps only); a new directory needs a README.
14. Shared files (`src/saber_tooth/api/__init__.py`, `src/saber_tooth/service/README.md`, `docs/api.md`, `tests/README.md`, `frontend/src/api/client.ts`, `frontend/src/pages/MapPage.tsx`, `frontend/tests/README.md`) get anchored `Edit` calls that add lines; never rewrite or reformat them.

## Review Focus

Input classes the spec implies but no requirement names, most likely first. Each line names the test that pins it.

1. Maps with BPM changes mid-window: the bar grid in beats is fixed but seconds are not. Pinned by `test_phrase_grid_with_bpm_change` (Task 1), `test_band_is_measured_in_seconds_across_a_tempo_change` (Task 5) and `test_bpm_changes_inside_the_window_are_kept_and_retimed` (Task 6).
2. Maps in v2, v3 and v4 form: v2 and v4 have no raw arc, chain or box lists, v4 tempo comes from AudioData, v3 carries raw lists that must be trimmed. Pinned by `test_every_map_version_crops_and_reads_back` (Task 6).
3. Songs with no analysis: `map_only` sections, no grid drift. Pinned by `test_without_analysis_sections_are_map_only` (Task 4) and `test_timeline_of_an_unscanned_map_is_map_only` (Task 10).
4. Very short or silent intros: anchor skips a note-free intro; a first note at the window start is padded to 2 s. Pinned by `test_anchor_skips_a_note_free_intro` (Task 1) and `test_lead_in_puts_the_first_note_two_seconds_in` (Task 6, includes first note at the cut).
5. 360, 90 or Lightshow-only characteristics: the loader keeps only `Standard`, so such a map has no difficulties and must be refused with a reason, not crash. Pinned by `test_map_without_standard_notes_is_refused` (Task 10) and `test_timeline_without_standard_notes_is_422` (Task 11).

---

## Tasks

1. [Task 1: Errors, bar and phrase grid, shared test helpers](task-01a.md)
1. [Task 1: Errors, bar and phrase grid, shared test helpers](task-01b.md)
1. [Task 2: NPS series](task-02.md)
1. [Task 3: Pitched tracks in the analyser reader](task-03.md)
1. [Task 4: Section detection](task-04.md)
1. [Task 5: Window search and snap points](task-05a.md)
1. [Task 5: Window search and snap points](task-05b.md)
1. [Task 6: Shift, trim, lead-in and light fades (pure)](task-06a.md)
1. [Task 6: Shift, trim, lead-in and light fades (pure)](task-06b.md)
1. [Task 7: ffmpeg cut and Info.dat fields](task-07.md)
1. [Task 8: Write the cropped folder](task-08.md)
1. [Task 9: Timeline assembly and window resolution](task-09a.md)
1. [Task 9: Timeline assembly and window resolution](task-09b.md)
1. [Task 10: Service functions and the crop job body](task-10.md)
1. [Task 11: API routes and 422 validation](task-11.md)
1. [Task 12: MCP tools](task-12.md)
1. [Task 13: Frontend types, client, query hook, pure crop helpers](task-13a.md)
1. [Task 13: Frontend types, client, query hook, pure crop helpers](task-13b.md)
1. [Task 14: NpsChart SVG component](task-14a.md)
1. [Task 14: NpsChart SVG component](task-14b.md)
1. [Task 14: NpsChart SVG component](task-14c.md)
1. [Task 15: CropPanel with snapping, keyboard and states](task-15a.md)
1. [Task 15: CropPanel with snapping, keyboard and states](task-15b.md)
1. [Task 16: MapPage wiring](task-16.md)
1. [Task 17: End-to-end fixture test](task-17.md)
1. [Task 18: Docs](task-18.md)

## Spec Coverage

1. User requirements 1 to 7: panel and switch (Task 15), suggestion by NPS with a rise (Tasks 5, 9), NPS chart (Task 14), cuts on section boundaries (Tasks 4, 5), band (Task 5), drag and snap (Tasks 13 to 15), new folder like Fix (Task 8).
2. Backend modules: phrases (1), sections (3, 4), nps (2), window (5), write (6 to 8).
3. API: timeline and crop (Task 11), validation 422 (Tasks 9, 11), MCP (Task 12).
4. Frontend states: skeleton, map only, reset, keep start on length switch, Create disabled during a job, job banners (Task 15), page wiring (Task 16).
5. Error handling: no notes (Tasks 9 to 11), short song (Task 5, 15), 422 (Tasks 9, 11), ffmpeg failure cleans up (Task 8), numbered name (Tasks 8, 17).
6. Testing: unit tests (Tasks 1 to 6, 9), hypothesis property (Task 5), writer tests (Tasks 6 to 8), end to end (Task 17), vitest (Tasks 13 to 16).
