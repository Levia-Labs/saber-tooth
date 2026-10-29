# pages

One component per route.

1. `LibraryPage.tsx`: `/`, the library with filters, sorting and live status.
2. `MapPage.tsx`: `/maps/:id`, findings, proposals and scan, approve all and apply.
3. `NewPage.tsx`: `/new`, one card: YouTube link or dropped audio file, one Generate button, progress and result as toasts, then the new map page.
4. `NotFoundPage.tsx`: any other path.
5. `BeatSaverPage.tsx`: `/beatsaver`, search, filter and download BeatSaver maps.
6. `BeatSaverPlaylistsPage.tsx`: `/beatsaver/playlists` and `/beatsaver/playlists/:id`, playlist search and their maps.
7. `JobsPage.tsx`: `/jobs`, one table of every job (kind and status, Cancel on queued and running, title link, cover or kind icon, length) with sort toggles and status, kind and title filters kept in the URL.
