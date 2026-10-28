# components

Shared UI.

1. `icons.tsx`, `Logo.tsx`: own SVG icon set and the logo mark.
2. `Tip.tsx`, `Buttons.tsx`: tooltips and icon or text buttons and links.
3. `Chips.tsx`: status chip, level chips, cover and tempo.
4. `Announcer.tsx`: announcement toasts (progress, success, warning, danger, info) in the bottom stack, with optional link, action buttons, a sticky flag and an onDismiss hook; `useWithdraw` removes one by key.
5. `FilterBodies.tsx`, `TextFilterBody.tsx`, `FilterPopover.tsx`, `MobileFilters.tsx`: column filters as popovers and as a fullscreen sheet.
   5a. `SectionTabs.tsx`: Library | BeatSaver tabs in the page title slot, with a visually hidden h1.
6. `LibraryHeader.tsx`, `LibraryTable.tsx`, `LibraryRow.tsx`, `SkeletonRow.tsx`: the virtualised library table.
7. `ProposalCard.tsx`, `ProposalGroups.tsx`, `TimelineCanvas.tsx`: proposed fixes with before and after note grids.
8. `ConfirmDialog.tsx`, `JobOutcome.tsx`: confirmation dialog and the toast for a finished scan, apply or learn job (Try again, Review as toast actions).
9. `beatsaver/`: the BeatSaver view: table, row, header, filter bodies, presets bar, selection bar, download hooks and playlist list.
10. `Alert.tsx`: danger, warning, info and success alerts; [alerts.ts](../lib/alerts.ts) maps jobs and errors to them.
11. `Skeletons.tsx`: layout-matching loading placeholders for the map page and route fallback.
12. `FixButton.tsx`: the primary Fix action; its result shows as a keyed toast (see `../lib/fixToast.ts`).
13. `NpsChart.tsx`: hand-written SVG notes-per-second chart for the crop panel: section bands, window handles, end marks.
14. `CropPanel.tsx`: the Crop tab body, mounted when the tab first shows and loading the crop timeline; length switch, free-drag chart, Save and Reset, job banners and result link. With `steps` (VR layout) the large step buttons of `CropSteps.tsx` show under the chart. It posts song seconds; the server converts them to beats.
15. `CropSave.tsx`: "Save as new map" and "Save over this map" (warning style, `ConfirmDialog` with the danger option; hidden while a job runs).
16. `MapFooter.tsx`: footer row on the map page: previous title, `index / total`, next title, from `GET /api/maps/{id}/neighbors` with the Library's last query (kept in sessionStorage); hidden when the request fails.
17. `DropZone.tsx`: audio drop target and keyboard-reachable picker used by the generate page.
