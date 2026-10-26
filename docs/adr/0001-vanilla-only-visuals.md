# 0001 Vanilla-only visuals

## Context

Many installed maps get striking visuals from mods such as Chroma, Noodle Extensions and Vivify. Those mods add requirements for players and are outside what the owner of the library wants. Some installed maps also reach a modern look with vanilla features only: environment choice, v3 event box lighting and colour schemes.

## Decision

1. No map written by saber-tooth requires or suggests Chroma, Noodle Extensions, Vivify, Heck or any other gameplay or visual mod.
2. The lightshow learner indexes the vanilla techniques of installed maps (event types, event box group shapes, events per beat, colour schemes) and the applier reuses them.
3. Output files carry no `customData` keys.

## Consequences

1. Maps load on an unmodded game.
2. Visual range is limited to what vanilla lighting can do. The quality bar is met through timing and structure of the lights, not through mod effects.
3. Maps that rely on mods are only learned from for their vanilla parts.
