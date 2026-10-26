# tests/fixtures/analyser

1. `song1/`: beat-analyser project output for one song, read by `tests/test_analysis.py` through [analysis.py](../../../src/saber_tooth/analysis.py).

Files in `song1/`:

1. `meta.json`: song metadata (name, key and related fields).
2. `beats.csv`: the beat grid.
3. `kick.csv`, `snare.csv`, `hh.csv`: drum onsets.
4. `bass.csv`, `melody.csv`, `chords.csv`: pitched content.

Run: `task st:test -- tests/test_analysis.py`.
