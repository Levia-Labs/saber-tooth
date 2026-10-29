# components

Shared UI.

1. `icons.tsx`, `Logo.tsx`: own SVG icon set and the logo mark.
2. `Tip.tsx`, `Buttons.tsx`: tooltips and icon or text buttons and links.
3. `Chips.tsx`: status chip, level chips, cover and tempo.
4. `Announcer.tsx`: announcement toasts (progress, success, warning, danger, info) in the bottom stack, with optional link, action buttons, a sticky flag and an onDismiss hook; an input with `onOpen` renders as one row (`ToastRow.tsx`: icon, title, rounds, X) whose body opens the Jobs page; `useWithdraw` removes one by key.
5. `FilterBodies.tsx`, `TextFilterBody.tsx`, `FilterPopover.tsx`, `MobileFilters.tsx`: column filters as popovers and as a fullscreen sheet.
   5a. `PillTabs.tsx`, `SectionTabs.tsx`: the segmented tab bar (icon and label per tab, arrow keys move focus, optional count badge) and the section tabs built on it: Library, BeatSaver, Jobs, Playlists, About (one `ITEMS` array of path, label, icon), the Jobs tab with the active job count, and a visually hidden h1. The BeatSaver Maps / Playlists tabs reuse `PillTabs`.
6. `LibraryHeader.tsx`, `LibraryTable.tsx`, `LibraryRow.tsx`, `SkeletonRow.tsx`: the virtualised library table.
7. `ProposalCard.tsx`, `ProposalGroups.tsx`, `TimelineCanvas.tsx`: proposed fixes with before and after note grids.
8. `ConfirmDialog.tsx`, `JobOutcome.tsx`: confirmation dialog and the toast for a finished scan, apply or learn job (Try again, Review as toast actions).
9. `beatsaver/`: the BeatSaver view: table, row, header, filter bodies, presets bar, selection bar, download hooks and playlist list.
10. `Alert.tsx`: danger, warning, info and success alerts; [alerts.ts](../lib/alerts.ts) maps jobs and errors to them.
11. `Skeletons.tsx`: layout-matching loading placeholders for the map page and route fallback.
12. `FixButton.tsx`: the primary Fix action; its result shows as a keyed toast (see `../lib/fixToast.ts`).
13. `NpsChart.tsx`: hand-written SVG notes-per-second chart for the crop panel: section bands, window handles, end marks.
14. `CropPanel.tsx`: the Crop tab body, mounted when the tab first shows and loading the crop timeline; length switch, free-drag chart, Save and Reset, job banners and result link. It posts song seconds; the server converts them to beats.
15. `CropSave.tsx`: "Save as new map" and "Save over this map" (warning style, `ConfirmDialog` with the danger option; hidden while a job runs).
16. `MapFooter.tsx`: footer row on the map page: previous title, `index / total`, next title, from `GET /api/maps/{id}/neighbors` with the Library's last query (kept in sessionStorage); hidden when the request fails.
17. `DropZone.tsx`: audio drop target and keyboard-reachable picker used by the generate page.
18. `StepButtons.tsx`: up and down arrow column beside a number input; holding repeats (used by `RangeFilterBody.tsx`).
19. `JobToasts.tsx`: restores one-row toasts for running jobs (never queued ones; no buttons, click opens the Jobs page), takes over jobs whose page unmounted, folds more than 4 into one summary.
20. `JobsTable.tsx`, `JobsHeader.tsx`, `JobsRow.tsx`, `JobsFilterBody.tsx`, `JobStatusChip.tsx`: the Jobs tab table (columns mirror the library: Icon, Title, Length, Operation, Status chip, Queue #, Rounds, Actions with a trash Cancel job), its sortable filterable header, rows and multi-select filter body.
21. `playlists/`: `LpTable.tsx` (the Playlists table: Icon, Title, Songs, Folder, Sync, Actions; sort and filter in the header), `LpEditor.tsx` (name, author, description, cover, songs, subfolder, sync and the PlaylistManager refresh hint) and `LpSongPicker.tsx` (library search, job output, latest generated or fixed).
