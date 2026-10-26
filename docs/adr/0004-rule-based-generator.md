# 0004 Rule-based generator

## Context

The service must place notes for five difficulties from beat and onset data. The quality bar requires zero findings from every check rule, with natural parity and flow. Machine-learning generation is a non-goal.

## Decision

1. The generator is rule-based. Inputs are the beat grid, kick, snare and hi-hat onsets, and bpm.
2. A per-hand parity state machine, forehand or backhand, chooses cut directions.
3. Position rules forbid resets without a bomb and keep every swing within reachable distance.
4. A per-difficulty profile sets target notes per second, NJS, offset, minimum gap between same-hand swings and allowed patterns. Easy uses singles on strong beats only. ExpertPlus allows streams and doubles and forbids crossovers.
5. Generated output is validated by the same check functions used on existing maps.

## Consequences

1. Output is deterministic for the same input and testable with property tests: every generated difficulty passes every rule.
2. No training data or model runtime is needed.
3. Musical phrasing is limited to what the rules and onset data express, so the quality of flow depends on the rule set and needs tuning.
