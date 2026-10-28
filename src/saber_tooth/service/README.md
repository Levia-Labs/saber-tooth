# service

The layer between the CLI or HTTP routes and the engine modules. Routes are described in [api.md](../../../docs/api.md).

1. `core.py`: `Service`, library refresh, scan, generate, apply and learn.
2. `errors.py`: `MapNotFound`, `MapUnreadable`, `ApplyConflict`, `DeleteRefused`.
3. `util.py`: pure helpers for map ids, finding keys and op spans.
4. `writeout.py`: writes output folders, never into an existing map folder.
5. `fix.py`: one-click fix engine behind `Service.fix_map`; every fix verified against the map the earlier fixes left.
6. `lightshow_set.py`: picks the learned or bundled lightshow set and reports it for `GET /api/lightshow`.
7. `delete.py`: `DeleteMixin.delete_map` removes a map folder from disk (guarded to direct children of the levels folder) and its rows from the store.
8. `crop.py`: crop highlight, attached as `Service.crop_timeline`, `crop_check` and `crop_map`; the timeline uses the stored scan analysis and never calls the analyser.

Storage is in [store.py](../store.py). Tests: `task st:test -- tests/test_service.py tests/test_service_more.py`.
