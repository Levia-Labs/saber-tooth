# saber_tooth

The application package. Module design is in [architecture](../../docs/architecture.md).

Subpackages:

1. [mapio/](mapio/README.md): read and write Beat Saber maps.
2. [checks/](checks/README.md): one pure function per quality rule.
3. [fixer/](fixer/README.md): turns findings into verified edit proposals.
4. [generator/](generator/README.md): rule-based note placement.
5. [lightshow/](lightshow/README.md): learn and apply lightshow templates.
6. [service/](service/README.md): library refresh, scan, generate, apply and learn.
7. [web/](web/README.md): static browser UI.

Top-level modules:

1. `model.py`: internal map model (notes, bombs, walls, events, difficulties).
2. `profiles.py`: per-difficulty generation profiles.
3. `analysis.py`, `analyser_client.py`, `audio.py`: beat-analyser output, its HTTP client and audio conversion.
4. `timing.py`, `swings.py`: beat and time conversion, swing geometry.
5. `assemble.py`: builds a map from generator output.
6. `store.py`, `jobs.py`: SQLite storage and background jobs.
7. `safe_fs.py`: path safety helpers.
8. `cli.py`: the `saber-tooth` command line.

Test with `task st:test`.
