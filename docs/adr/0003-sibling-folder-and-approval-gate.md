# 0003 Sibling-folder output and approval gate

## Context

The maps in `CustomLevels` are the user's library. An automatic repair that overwrites a map, or a wrong fix that goes unnoticed, damages work that is hard to restore.

## Decision

1. Every change is a proposal. Nothing is written until the user approves it. Bulk approval exists only as an explicit per-map action.
2. Fixes go into a new sibling folder named `<original name> [saber-tooth]`, and the `_songName` in Info gains the same suffix. A second apply writes `[saber-tooth 2]`.
3. Writes go to a temporary folder, then an atomic rename. An existing target name is refused.
4. Apply re-runs the checks on the staged result and aborts if any applied operation produces a new finding.
5. A write guard in the filesystem layer refuses any write inside a folder that existed when the writer was created. A test asserts this.

## Consequences

1. The original map is never at risk.
2. The library shows both versions and the user chooses in game.
3. Disk use grows with each repaired map.
4. The user performs an approval step for every change.
