# tests

Vitest suites run with `task st:web:test`.

1. `setup.ts`: jest-dom matchers, jsdom layout and matchMedia stubs, cleanup.
2. `helpers.tsx`: map fixtures, fetch mock and an app renderer on a memory router.
3. `urlstate.test.ts`: URL and API parameter encoding, sort rules and property tests.
4. `formatting.test.tsx`: formatters, level chips and contrast, status chips and tooltip copy.
5. `library.test.tsx`: skeleton rows, rows, filters, popover keyboard use and live status.
6. `timeline.test.ts`: note grid and wall geometry.
7. `pages.test.tsx`: map page, approve flows, generate form, 404 and back link.
8. `fixes.test.tsx`: touch long-press tooltips, search flush on close and approve all errors.
9. `delete.test.tsx`: Delete button, confirm dialog, permanent delete, banner and error path.
10. `crophelpers.tsx`, `croplib.test.ts`, `cropchart.test.tsx`, `croppanel.test.tsx`, `cropwiring.test.tsx`, `vrmap.test.tsx` (VR map screen): the crop timeline fixture and API stub, snapping helpers, the SVG chart, the panel states and its place on the map page.
11. `vrstatus.test.tsx`, `vrmodepure.test.ts`, `vrmode.test.tsx`: the VR status poll, the pure mode decision and the `VrModeProvider` redirects, attribute and banner. `vrshell.test.tsx`: the Shell wiring (suggestion toast, masthead switch, remembered mode).
12. `vrcss.test.ts`: reads `../src/styles/vr.css` as text and pins the 22 px, 64 px and 16 px sizes, the scoping, focus ring, hidden tooltips and grid.
13. `vrroutes.test.tsx`: `/vr`, `/vr/maps/:id` and `/vr/beatsaver` render the desktop pages under the VR styling. `vrshell.test.tsx` also covers `/vr/jobs`. `vrcss.test.ts` pins the 2x sizes.
14. `generate.test.tsx`, `proposalbuttons.test.tsx`: the one-step generate card (link, drop, toasts, navigation) and the Approve and Reject button states.
15. `clock.test.ts`, `filterpopovers.test.tsx`: the mm:ss helper (invalid input, round trip) and the filter popover bodies (one Author input, mm:ss Length row, clear at the row end, lists that scroll).
16. `holdrepeat.test.tsx`, `rangesteppers.test.tsx`: the hold-repeat hook and `stepBound` (fake timers), and the Length and BPM inputs (placeholders from facets, integer-only BPM, arrows and arrow keys).
17. `jobtoasts.test.ts`, `jobtoastsApp.test.tsx`: the pure toast plan and the app watcher (refresh restore, summary, empty stubs, navigation hand-off).
