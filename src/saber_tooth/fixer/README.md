# fixer

Turns findings from [checks](../checks/README.md) into proposals. A proposal is a list of edit operations that is accepted only if it passes verification.

1. `ops.py`: frozen, JSON-serialisable edit operations applied purely to a `Beatmap`.
2. `codec.py`: JSON-safe conversion of model objects used by operations.
3. `strategies.py`, `layout_fixes.py`, `map_fixes.py`: candidate generators per rule, yielded in preference order.
4. `cells.py`: grid and swing helpers shared by strategies.
5. `verify.py`: the proposal model and the acceptance check every candidate must pass.
6. `thin.py`: thin a denser difficulty down to a tier's target density, then re-flow its cuts.
7. `summary.py`: short human sentences describing a list of operations.
8. `__init__.py`: public entry points.

Tests: `task st:test -- tests/test_fixer.py`. Design: [architecture](../../../docs/architecture.md).
