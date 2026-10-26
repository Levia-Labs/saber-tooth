# service

The layer between the CLI or HTTP routes and the engine modules. Routes are described in [api.md](../../../docs/api.md).

1. `core.py`: `Service`, library refresh, scan, generate, apply and learn.
2. `errors.py`: `MapNotFound`, `MapUnreadable`, `ApplyConflict`.
3. `util.py`: pure helpers for map ids, finding keys and op spans.
4. `writeout.py`: writes output folders, never into an existing map folder.

Storage is in [store.py](../store.py). Tests: `task st:test -- tests/test_service.py tests/test_service_more.py`.
