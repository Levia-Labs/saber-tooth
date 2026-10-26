# web

Static HTML, CSS and vanilla JS served at `/` by the app. There is no build step and no external resources ([ADR 0001](../../../docs/adr/0001-vanilla-only-visuals.md)).

1. `index.html`: page shell that loads the assets.
2. `style.css`: styles.
3. `favicon.svg`: tab icon.
4. `app.js`: entry point, library and map detail views.
5. `cards.js`: finding and proposal cards.
6. `timeline.js`: canvas drawing of before and after note windows.
7. `newmap.js`: the new-map form.
8. `util.js`: DOM helpers, API calls and job polling.

Routes used are in [api.md](../../../docs/api.md). Tests: `task st:test -- tests/test_web.py`.
