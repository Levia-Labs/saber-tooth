# lightshow

Learns lightshow templates from installed maps and applies them to new ones. Overview: [architecture](../../../docs/architecture.md).

1. `learn.py`: `learn`, indexes maps per environment into templates.
2. `units.py`: `Unit` and `Templates`, the stored template shape.
3. `energy.py`: `bar_energy`, per-bar energy from the analysis.
4. `apply.py`: `build_lightshow` and `choose_environment`, which pick a template and retime it onto the beat grid.

5. `data/templates.json.gz`: the bundled learned set; see [data/README.md](data/README.md).

Tests: `task st:test -- tests/test_lightshow_learn.py tests/test_lightshow_apply.py`. CLI: `task st:learn -- <levels_dir> <out.json>`.
