# vr

The VR layout: mode decision, headset status, screens and the CSS hooks they use. See [the VR mode design](../../../docs/superpowers/specs/2026-10-28-vr-mode-design.md).

1. `status.ts`: `GET /api/vr/status` client, query options and the 5 s visibility-aware poll.
2. `mode.ts`: the pure mode decision (URL, remembered choice, headset browser, default), storage helpers, `/vr` path mapping and the WebXR probe.
3. `VrMode.tsx`: `VrModeProvider` and `useVrMode`: the decided mode, headset status, banner state, `choose`, the `data-ui` attribute and the redirects between desktop and VR paths.
4. `presets.ts`, `VrNav.tsx`, `useNearEnd.ts`, `VrCard.tsx`, `VrLibraryPage.tsx`: the `/vr` Library screen (presets map onto the library query, state in the address, more cards on scroll).
5. `VrMapPage.tsx`: the `/vr/maps/:id` screen; it reuses `CropPanel` with `steps` (the large step buttons of `../components/CropSteps.tsx`).
6. `VrBsCard.tsx`, `VrBsPlaylists.tsx`, `VrBeatSaverPage.tsx`: the `/vr/beatsaver` screen (preset toggles, sort, cursor paging on scroll, playlists, large Download per card, the shared download summary toast; no text search).
