# web

Build output of the React frontend. `task st:web:build` (or the `web` stage of the Dockerfile) runs `vite build` in [frontend](../../../frontend/README.md), which writes `index.html` and the hashed `assets` folder here; the app serves this folder at `/`. Everything except this README is git-ignored. There are no external resources ([ADR 0011](../../../docs/adr/0011-react-typescript-vite-frontend.md)).

1. `index.html`: the single page; served for `/`, `/maps/<id>` and `/new` with `Cache-Control: no-cache`.
2. `assets`: content-hashed JS, CSS and the favicon; served with `Cache-Control: public, max-age=31536000, immutable`.

Without a build the API and MCP routes still work, but `/` answers 404. Routes used are in [api.md](../../../docs/api.md). Tests: `task st:web:test` and `task st:test -- tests/test_web.py`.
