# crop

Crops a map to a 1 or 2 minute highlight on song-part boundaries. Plan: [crop-highlight](../../../docs/superpowers/plans/crop-highlight/index.md).

1. `errors.py`: `CropError`, `NoNotes` and `InvalidWindow`; the API turns a `CropError` into HTTP 422.
2. `phrases.py`: `Grid`, `build_grid` and `grid_drift`, the bar and 8-bar phrase grid of a map.
3. `nps.py`: `note_beats`, `nps_series`, `all_series`, `peak`, `mean_nps` and `slope`, the 1 s notes per second series.
4. `sections.py`: `Section`, `SectionMap` and `find_sections`, song sections from change scores over map and audio terms.
5. `window.py`: `TARGETS`, `band`, `build_plan` and the `CropPlan`, `StartPoint`, `EndPoint` and `Window` types, the suggested stretch and every allowed start and end.
6. `shift.py`: `Cropped`, `crop_difficulty` and `crop_beatmap`, the pure shift, trim, lead-in and light fade of a map to a beat window.
7. `info.py`: `crop_info`, the song name suffix and in-range preview of a cropped map.
8. `write.py`: `FADE_IN_S` and `write_cropped`, the cropped folder written through `LevelsWriter` with the cut song and the cover.

Tests: `task st:test -- tests/test_crop_phrases.py tests/test_crop_nps.py tests/test_crop_sections.py tests/test_crop_window.py tests/test_crop_shift.py tests/test_crop_info.py tests/test_crop_write.py`.
