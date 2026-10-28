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
10. `crophelpers.tsx`, `croplib.test.ts`, `cropchart.test.tsx`, `croppanel.test.tsx`, `cropwiring.test.tsx`: the crop timeline fixture and API stub, snapping helpers, the SVG chart, the panel states and its place on the map page.
11. `vrstatus.test.tsx`, `vrmodepure.test.ts`, `vrmode.test.tsx`: the VR status poll, the pure mode decision and the `VrModeProvider` redirects, attribute and banner.
12. `vrcss.test.ts`: reads `../src/styles/vr.css` as text and pins the 22 px, 64 px and 16 px sizes, the scoping, focus ring, hidden tooltips and grid.
13. `vrhelpers.tsx`, `vrpresets.test.ts`, `vrlibrary.test.tsx`: the VR render and observer helpers, the pure presets and sorts, and the `/vr` Library screen (cards, presets, sort, scroll loading).
