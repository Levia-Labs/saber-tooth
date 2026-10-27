# tests

pytest suite. Run all with `task st:test`, or pass a path: `task st:test -- tests/test_mapio.py`.

Files follow the package modules: `test_mapio`, `test_checks_*`, `test_fixer`, `test_generator`, `test_lightshow_*`, `test_service*`, `test_store`, `test_jobs`, `test_cli`, `test_web`, `test_web_cache`, `test_analysis`, `test_analyser_client`, `test_audio`, `test_assemble`, `test_swings`, `test_timing`, `test_safe_fs`. `test_readme_check.py` covers [scripts/readme_check.py](../scripts/README.md), `test_script_*.py` cover the workflow scripts, and `test_smoke.py` is a minimal import check.

Test data is in [fixtures](fixtures/README.md). Strategy: [architecture](../docs/architecture.md).
