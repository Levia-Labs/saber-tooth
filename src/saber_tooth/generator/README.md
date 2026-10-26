# generator

Rule-based note placer. Inputs come from [analysis.py](../analysis.py) and a per-difficulty profile from [profiles.py](../profiles.py). Output is a `Difficulty`, checked with [checks](../checks/README.md).

1. `build.py`: `generate_difficulty`, `generate_with_stats` and `GenerationStats`.
2. `candidates.py`: candidate onsets per bar from the analysed audio.
3. `plan.py`: per-bar density planning.
4. `placer.py`: places notes and raises `GenerationError` when it cannot.
5. `motifs.py`: swing direction patterns.
6. `tempo.py`: `tempo_map`, BPM events from the beat grid.
7. `walls.py`: `place_walls`, walls only (no bombs) on Hard and above.

Tests: `task st:test -- tests/test_generator.py`. Design: [architecture](../../../docs/architecture.md).
