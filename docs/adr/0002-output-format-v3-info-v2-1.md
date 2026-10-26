# 0002 Output format: difficulty v3.3.0 and Info v2.1.0

## Context

Installed maps use Info v2.0.0, v2.1.0 and v4, and difficulties in v2, v3 and v4. Game version 1.45.3 loads all of them. v3 difficulties carry event box groups, which modern vanilla lighting needs. Info v2.1.0 supports `_environmentNames` and `_colorSchemes`, which give per-difficulty environment and colour scheme.

## Decision

1. The reader accepts every format found in the library and converts it to one internal model.
2. The writer emits difficulty v3.3.0 and Info v2.1.0 only.
3. Unknown keys are preserved when the source is v3.
4. v4 BPM changes are ignored in v1 and tracked in the TODO list.

## Consequences

1. One writer to test and one output shape to document.
2. Old v2 maps are upgraded when repaired into a sibling folder.
3. v4 sources lose nothing needed for checks, but their BPM changes are not honoured until the TODO is done.
