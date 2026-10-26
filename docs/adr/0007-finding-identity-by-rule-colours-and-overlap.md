# 0007 Finding identity by rule, colours and overlapping beats

## Context

Apply must refuse a result that adds a problem, and the fixer must accept only candidates that remove a finding without adding one. Both need a way to say that a finding after the change is the same as one before it. The first design identified a finding by its note cells (beat, column, row, colour). That rejected valid fixes: a fix that moves a note changes the cell, so the same underlying problem looked like a new one, and a fix that resolved it looked like it had added one.

## Decision

1. A finding is identified by difficulty, rule and the set of hand colours of its notes.
2. Two findings match when that identity is equal and their beat ranges overlap or touch, with a small tolerance.
3. A finding after a change that matches no finding before it is new.
4. Apply compares against the findings stored in the `scans` table by the last scan. If no scan exists it computes the baseline from the original map.

## Consequences

1. Moving, recolouring or flipping the notes of a finding no longer makes it look new.
2. A fix that shifts a problem a few beats along the same range is treated as the same problem. This is the intended reading.
3. Two distinct problems of the same rule and hands in an overlapping range are treated as one. A fix that swaps one for the other is not caught by this rule alone; remaining errors still abort apply.
