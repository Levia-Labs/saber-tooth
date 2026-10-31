# TODO

Add entries with `task todo:add`.

## 2 Flaky backend job-wait in tests/test_api.py _wait (200x50 ms) under load; make the wait event-driven or longer

status: done
class: quality

## 3 Approve all updates the review banner late

status: done
class: bug

After Approve all on a map review, the banner keeps showing 'No fixes approved yet' for about 3 s before Apply approved enables. Seen 2026-10-28 while capturing website screenshots.

## 4 test_round_trip hypothesis deadline flakes

status: done
class: test

Gate run on 2026-10-28 failed once with DeadlineExceeded in test_round_trip (203 ms vs the 200 ms deadline) and passed on rerun. Raise or disable the deadline for that test, or shrink its inputs.

## 5 fixbutton danger-alert test flakes under full-suite load

status: done
class: test

frontend/tests/fixbutton.test.tsx 'a failed job shows a danger alert with the error' failed once in the full suite with 'Found multiple elements with the text: /Fix failed/' (job toast and inline alert both match) and passed in 3 isolated runs and a full-suite rerun. Scope the query to the toast stack or the alert region.

## 6 Flaky vrshell suggestion-toast test

status: done
class: bug

tests/vrshell.test.tsx 'suggestion toast > accepting switches to the VR layout and remembers it' failed once under st:gate load (element not found); passed alone and in a full vitest rerun on 2026-10-29. Likely a missing findBy/waitFor.

## 7 Running-job toasts have no close button

status: done
class: bug

frontend/src/components/Announcer.tsx passes no onDismiss for the progress variant, so the per-job dismissed set in planToasts (frontend/src/lib/jobtoasts.ts) is never fed from the UI.

## 8 Non-progress job handlers ignore cancel

status: done
class: bug

In src/saber_tooth/jobs.py terms: scan, apply, learn, generate, crop and bs-download never call progress or check(), so DELETE on a running one returns 200 with cancel_requested true and the job still ends done.

## 9 CropSteps steps mode may be dead after VR card removal

status: done
class: cleanup

frontend/src/components/CropSteps.tsx steps mode was used by the removed VR map page; docs/vr.md 'Crop steps in VR' still describes it. Confirm unused, then remove or rewire.

## 10 Checks are not incremental on large maps

status: done
class: perf

Each fix proposal re-runs a full difficulty check (~0.17 s per finding on a 7102-finding map). Batched per-level scan/fix work is in progress; if checks stay whole-difficulty, make the rules incremental over a time window.

Done: check_difficulty and run_checks take a beat window (checks/**init**.py, REACH_S declares each rule's reach, empty-gap is global and bisects its gaps); scan checks per batch window; verify and dot_reach bisect instead of scanning the difficulty. Proposing on a 3400-note, 9811-finding map: 40.6 to 17.6 ms per finding (scripts/profile_checks.py). apply_ops now bisects and inserts into owned sorted notes (fixer/ops.py, cow.py), 17.6 to 9.9 ms per finding; full Fix of the 3400-note map 131 s to 60 s with identical steps. Remaining: apply_ops still copies the note list per candidate and each proposal runs 5-8 candidates, so cost is O(N) memcpy plus the window checks.

## 11 Status tab does not show why Fix left a finding unfixed

status: open
class: feature

The unfixed reasons live only in the Fix job result keyed to the original map and the checkpoint is cleared on finish; persist them per copy (e.g. on the copy's scan row) and show them on FindingCard next to 'No automatic fix'.

## 12 Flaky frontend test: pages.test.tsx 'Map not found'

status: open
class: test

Failed once in a full st:web:test run during the delete-flow change and passed on rerun; find the timing dependency (unawaited fetch or shared state) and make it deterministic.
