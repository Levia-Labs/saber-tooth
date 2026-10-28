# Crop highlight design

Date: 2026-10-28. Status: design approved in conversation; written spec pending review.

## Goal

Turn any map into a 1 or 2 minute highlight: the most intense stretch of the song by notes per second (NPS),
opening on a build-up, with both cut points on song-part boundaries so no verse, chorus or drop is cut in half.
The result is a new playable folder; the original is never changed.

## User requirements

1. The map page offers a crop to 1 minute or 2 minutes.
2. The suggested window is the most intense one by NPS and starts with a rise into the peak.
3. An NPS chart shows the whole song so the user can see and choose the timing.
4. Cuts follow song parts: never mid-verse, mid-chorus or mid-drop.
5. Length may differ from the target by up to 10 percent either way: 1 min is 54 to 66 s, 2 min is 108 to 132 s.
6. The user can drag the window; its edges snap to allowed points only.
7. Output is a new folder beside the original, like Fix output.

## Terms

1. Bar: four beats on the map's tempo grid, including BPM changes.
2. Phrase: 8 bars, counted from the first downbeat that carries notes.
3. Section: a run of phrases between two section boundaries; at least 8 bars long.
4. Band: the allowed length range, target length plus or minus 10 percent.

## Architecture

### Backend (`src/saber_tooth/crop/`)

Each module has one job and is tested on its own.

1. `phrases.py`: the bar and phrase grid from the map's timing, cross-checked against beat-analyser beats when the
   song has been analysed.
2. `sections.py`: a change score per phrase start, the sum of normalised jumps between the 8 bars before and the
   8 bars after in:
   1. drum onset rate (kick, snare, hi-hat);
   2. bass and chord note rate;
   3. melody note rate and pitch range;
   4. light events per bar in the map;
   5. note density in the map.

   Scores above the song's 70th percentile are section boundaries; boundaries closer than 8 bars keep the higher
   score. Without analysis only the two map terms count and the result is flagged `map_only`.

3. `nps.py`: notes per second per difficulty in 1 s steps, bombs excluded, a chain counted as one note; plus the mean
   NPS of each section.
4. `window.py`: the suggestion and the snap points.
   1. Start: always a section boundary.
   2. End, first match inside the band: a section boundary, else a phrase start, else a 4-bar line, else a bar line.
   3. Score per start, paired with its best end: 0.7 times the mean NPS of the hardest difficulty over the window,
      plus 0.3 times a build-up bonus (the first section's NPS is below the next section's and its NPS slope is
      positive), minus 0.1 when the end is not a section boundary. NPS terms are normalised to the
      song's peak.
   4. Output: the best window, the next two, every start point, and per start the allowed end points with their kind
      (`section`, `phrase`, `bar4`, `bar`).
5. `write.py`: writes `<original> [1 min]` or `<original> [2 min]` through the existing safe folder writer.
   1. Audio: ffmpeg cut with a 0.5 s fade-in and a fade-out over the last bar.
   2. Every difficulty: notes, walls, arcs, chains, bombs, lights and BPM changes shifted to the new start, with a
      lead-in so the first note is at 2 s or later.
   3. Notes, arcs and chains that cross a cut edge are dropped; walls are trimmed to the window.
   4. BPM changes inside the window are kept and re-timed.
   5. Lights fade in at the start and black out at the end so no light is left on.
   6. Info.dat: song name suffix, duration, preview start inside the new audio.
   7. Note 2026-10-28: Info.dat gets no duration field, because the v2.1.0 writer has none and the cut audio carries
      the length. Per-section mean NPS is computed in `sections.py` (`Section.nps`), not in `window.py`.

### API

1. `GET /api/maps/{id}/timeline`: NPS per difficulty, sections with intensity, `map_only`, and for each target length
   the suggested windows and snap points. Times are given in beats and seconds.
2. `POST /api/maps/{id}/crop` with `{start_beat, end_beat}`: validates the pair against the snap points and the band,
   starts a `crop` job, returns `{job}`. The finished job result names the new folder and map id.
3. MCP: `map_timeline` and `crop_map` tools with the same contracts.

### Frontend (`/maps/:id`)

1. A Crop panel with a 1 min / 2 min switch, the NPS chart, a length readout and a "Create cropped map" button.
2. Chart: hand-written SVG, one line per difficulty with the hardest emphasised, sections as shaded bands, the
   suggested window as the selection, the next two as faint bands.
3. Dragging: the start handle snaps to section boundaries; the end handle snaps to the allowed end points, each marked
   by kind. The readout shows the exact length and turns amber when the end is not a section boundary.
4. Keyboard: arrow keys move the focused edge to the next or previous allowed point; Shift+arrow jumps a section.
5. Hover shows time, section and NPS per difficulty.
6. States: skeleton while loading; "Sections from map only" when there is no analysis; "Reset to suggestion" after a
   drag; switching length keeps the start when it can and re-picks the end; Create is disabled while a job runs on
   the map.
7. The crop job uses the keyed job banners: progress while it runs, success with a link to the new folder, danger on
   failure.

## Error handling

1. Timeline cannot be built (unreadable map, no notes in any difficulty): the panel shows a danger alert with the
   reason; the rest of the page works.
2. Song shorter than the band's upper bound: the panel says so with the numbers and that length is disabled.
3. Invalid `start_beat`/`end_beat`: HTTP 422 naming the rule broken.
4. ffmpeg or write failure: the job fails, the partial folder is removed by the existing cleanup, the banner shows the
   error.
5. Target folder name taken: a numbered name, never an overwrite.

## Testing

1. Unit (pytest, no real files):
   1. phrase grid with BPM changes;
   2. section scoring on synthetic songs with clear verse and chorus energy steps;
   3. NPS with chains and bombs;
   4. window search: band limits, end preference order, build-up bonus;
   5. hypothesis property: every suggested window lies inside the band and starts on a section boundary.
2. Writer (tmp folders): exact shift, walls trimmed at cuts, BPM re-timing, light blackout, 2 s lead-in, Info.dat
   fields, ffmpeg called with the expected cut and fade arguments.
3. End to end on a small fixture map: timeline, crop job, the written folder read back with zero structure errors.
4. Frontend (vitest): chart renders bands, drag snaps, keyboard snap, amber readout off a section end, Create posts
   the chosen beats.

## Non-goals

1. Crop lengths other than 1 and 2 minutes.
2. Free cutting at arbitrary times.
3. Changing the original folder.
4. Running Fix on the cropped copy automatically.

## Note 2026-10-28: free cutting

Supersedes the snap and band rules for `POST /api/maps/{id}/crop`.

1. Any window is accepted when `start_beat >= 0`, `end_beat > start_beat`, the end lies inside the song and the length (through the map's Timing, BPM changes included) is at least 1 second. Section boundaries, snap points and the 1 and 2 minute bands no longer gate the request.
2. 422 messages: `end_beat must be after start_beat`, `the window must be at least 1 second long`, `the window must lie inside the song`. 409 for a busy map is still checked first.
3. `GET /timeline` is unchanged, plus `min_length_s: 1.0`; suggestions, sections and snap points stay as guidance.
4. Label: `1 min` or `2 min` when the length is within the existing band, else `crop MmSSs` from the rounded length (`crop 3m00s`). The colon of `m:ss` is refused by the Windows-safe folder check, so `MmSSs` is used. Collisions are numbered by LevelsWriter.
5. The fade-out over the last bar is clamped to the window length; the lead-in rule is unchanged.

## Note 2026-10-28: replace mode

1. `POST /api/maps/{id}/crop` takes an optional `"replace": true`. The window rules and the 409-first busy check are unchanged.
2. The job stages the crop in a partial folder as before and reads it back with `load_map`. It then guards the original with `LevelsRoot.guard` (direct child of the levels folder, real directory, no symlink or junction), renames it to `.<name>.old.partial`, renames the partial to the original name and removes the old folder last. A failure before or during the swap restores the original and removes the partial.
3. `Store.reset_map` clears the map's row, scan, proposals and finished jobs (the running crop job stays); the library refresh adds the map back as not scanned. The result is `{"replaced": true, "folder": <original name>, "cropped_id": <same id>, ...}`.
4. MCP `crop_map` stays new-folder only.
