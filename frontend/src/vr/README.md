# vr

The VR layout: mode decision, headset status, screens and the CSS hooks they use. See [the VR mode design](../../../docs/superpowers/specs/2026-10-28-vr-mode-design.md) and [vr.md](../../../docs/vr.md).

1. `status.ts`: `GET /api/vr/status` client, query options and the 5 s visibility-aware poll.
2. `mode.ts`: the pure mode decision (URL, remembered choice, headset browser, default), storage helpers, `/vr` path mapping and the WebXR probe.
3. `VrMode.tsx`: `VrModeProvider` and `useVrMode`: the decided mode, headset status, banner state, `choose`, the `data-ui` attribute and the redirects between desktop and VR paths.
4. No VR-specific pages: VR is the desktop pages at 2x scale, with the same functions and layout. `../styles/vr.css` doubles the root font size, row and header heights, targets and gaps, and centers the column.
5. Routes in `App.tsx`: `/vr` mounts `LibraryPage`, `/vr/maps/:id` `MapPage`, `/vr/beatsaver` `BeatSaverPage` and `/vr/jobs` `JobsPage`; the server answers them with `index.html` on reload. `mode.ts` maps each desktop path to its `/vr` twin. BeatSaver playlists keep their desktop path and get the VR styling.
6. `VrBanner.tsx`, `ModeSwitch.tsx`: the headset suggestion (a sticky info toast in the bottom stack with Switch and Not now) and the VR / Desktop toggle group in the masthead; `Shell` in `../App.tsx` mounts `VrModeProvider` around the page. Their styles are in `../styles/vrmode.css`.
