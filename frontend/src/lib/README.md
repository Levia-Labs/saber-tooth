# lib

Pure helpers and small hooks.

1. `urlstate.ts`: library query state in the URL and in API parameters.
2. `format.ts`: duration, BPM and plural formatting.
3. `levels.ts`: difficulty chips, beatsaver colours and text contrast.
4. `status.ts`: status labels, icons and running states.
5. `announcements.ts`: banner state by key, cap of four, auto-dismiss expiry (not for sticky), optional actions and details; `specToInput` turns an alert spec into a toast.
6. `tips.ts`: tooltip copy.
7. `hooks.ts`: URL-backed library state, debounce, media query and document title.
8. `timeline.ts`: canvas geometry and drawing for the before and after note grids.
9. `bsfilters.ts`, `useBsState.ts`: BeatSaver filter state in the URL, API parameters and presets.
10. `bscolumns.ts`, `bstips.ts`, `preview.ts`: BeatSaver column set, tooltip copy and the single audio preview.
11. `fixreport.ts`, `fixToast.ts`: read the report of a finished fix job; build its toast (failed, incomplete, nothing to fix, fixed).
12. `crop.ts`: pure crop helpers: snapping, stepping and re-picking the window edges, and `sectionStep` and `moveWindowToSection` (next or previous section start).
13. `generate.ts`, `decisions.ts`: link and audio checks for the generate card, and which proposal decisions are still allowed.
14. `clock.ts`: pure `parseClock` and `formatClock` for the "mm:ss" length filter inputs.
15. `stepRange.ts`, `useHoldRepeat.ts`: clamped stepping of a range bound and the press-and-hold repeat hook of the arrow buttons.
16. `jobtime.ts`: elapsed-time text and the stale-minutes check for the Jobs page.
17. `jobtoasts.ts`: which job toasts to show from the server job list (keys, finish toasts, the more-than-4 summary); pure.
