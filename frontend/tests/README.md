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
