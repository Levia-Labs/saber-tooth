# checks

Quality rules. Each rule is a pure function that takes a map or difficulty and returns a list of `Finding`. The rule list is in [architecture](../../../docs/architecture.md).

1. `__init__.py`: registers the rules and exposes `check_difficulty`.
2. `finding.py`: the `Finding` dataclass, severities (`error`, `warn`) and grading helpers.
3. `constants.py`: thresholds shared with the generator so the two cannot drift apart.
4. `flow.py`: parity break, swing speed, wide jump.
5. `layout.py`: crossover, note in wall, stack conflict, vision block.
6. `gaps.py`: empty gap.
7. `structure.py`: missing difficulty.

Tests: `task st:test -- tests/test_checks_flow.py tests/test_checks_layout.py tests/test_checks_gaps.py tests/test_checks_structure.py`. Consumers: [fixer](../fixer/README.md), [generator](../generator/README.md).
