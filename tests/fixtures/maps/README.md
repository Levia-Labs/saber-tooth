# tests/fixtures/maps

Small map folders loaded by `load_map` in tests ([mapio](../../../src/saber_tooth/mapio/README.md)). Each holds an info file, difficulty files and a `song.ogg`.

1. `v2_basic/`: version 2 map with `info.dat`, `Hard.dat` and `ExpertPlusStandard.dat`. Used by the loader, writer and CLI tests.
2. `v2_bpm/`: version 2 map with BPM changes in `Expert.dat`.
3. `v3_boxes/`: version 3 map with event box groups in `Expert.dat`. Also used by the lightshow learner tests.
4. `v4_split/`: version 4 map with `Easy.beatmap.dat` and a separate `Lightshow.dat`.

Formats: [map-format](../../../docs/map-format.md). Run: `task st:test -- tests/test_mapio.py`.
