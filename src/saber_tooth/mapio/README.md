# mapio

Parses Beat Saber maps into the internal model in [model.py](../model.py) and writes them back. Formats: [map-format](../../../docs/map-format.md).

1. `discover.py`: finds the info file and difficulty files in a folder; `load_map`, `find_info`, `difficulty_path`.
2. `read_v2.py`, `read_v3.py`, `read_v4.py`: per-version difficulty readers.
3. `write.py`: `write_map`, copies assets from the source folder and writes the output files.
4. `errors.py`: `MapParseError` and name safety.

Tests: `task st:test -- tests/test_mapio.py`, using [fixtures](../../../tests/fixtures/maps/README.md). Parent: [saber_tooth](../README.md).
