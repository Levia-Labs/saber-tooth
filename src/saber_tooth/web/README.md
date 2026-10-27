# web

Static HTML, CSS and vanilla JS served at `/` by the app. There is no build step and no external resources ([ADR 0001](../../../docs/adr/0001-vanilla-only-visuals.md)). Pages are routed client-side with the History API: `/` library, `/maps/<id>` map page, `/new` generate page; the server answers those paths with `index.html`.

1. `index.html`: page shell, inline icon sprite and centered header; assets use absolute paths so deep links work.
2. `style.css`: tokens, header, buttons and tooltip; `library.css`: toolbar, table and the mobile list layout; `page.css`: status chips, map page and proposal cards.
3. `favicon.svg`: tab icon and source of the inline logo mark.
4. `app.js`: entry point; wires the router, tooltips and header buttons.
5. `router.js`: route matching, link interception, navigation and focus handling.
6. `urlstate.js`: library query state (search, status, sort) in the URL and in `GET /api/maps` parameters.
7. `library.js`: library page with filters, header sorting and infinite scroll.
8. `librows.js`: one library row with cover, status chip and actions.
9. `mappage.js`: map page with actions, findings and proposals.
10. `newmap.js`: the generate form and its proposal preview.
11. `chips.js`: status chips, difficulty pips and cover images.
12. `ui.js`: icon button and link builders with tooltip text.
13. `icons.js`: sprite icon helper.
14. `tooltip.js`: accessible tooltips and their placement math.
15. `tips.js`: tooltip copy.
16. `cards.js`: finding and proposal cards.
17. `timeline.js`: canvas drawing of before and after note windows.
18. `util.js`: DOM helpers, API calls and job polling.
19. `retry.js`: polling retry policy.

Routes used are in [api.md](../../../docs/api.md). Tests: `task st:test -- tests/test_web.py` and `npm run test:js`.
