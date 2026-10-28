# crop

Crops a map to a 1 or 2 minute highlight on song-part boundaries. Plan: [crop-highlight](../../../docs/superpowers/plans/crop-highlight/index.md).

1. `errors.py`: `CropError`, `NoNotes` and `InvalidWindow`; the API turns a `CropError` into HTTP 422.
2. `phrases.py`: `Grid`, `build_grid` and `grid_drift`, the bar and 8-bar phrase grid of a map.

Tests: `task st:test -- tests/test_crop_phrases.py`.
