# frontend

React 19, TypeScript and Vite single-page app that replaces the old hand-written web folder ([ADR 0011](../docs/adr/0011-react-typescript-vite-frontend.md)). `vite build` writes the bundle to `../src/saber_tooth/web/`, which FastAPI serves at `/`.

1. `package.json` and `package-lock.json`: exact pins; install with `npm ci`.
2. `vite.config.ts`: build output, dev proxy for `/api` and `/mcp` to `127.0.0.1:8100`, Vitest settings.
3. `eslint.config.js`: the shared Crepidoma config plus react-hooks and jsx-a11y rules.
4. `tsconfig.json`: strict TypeScript, `noEmit`.
5. `index.html`: Vite entry document.
6. `src/`: application code.
7. `tests/`: Vitest suites.

Tasks: `task st:web:build`, `task st:web:test`, `task st:web:check`. There is no dev server: check UI changes against the rebuilt service (`task st:up`).
