# 0011 React + TypeScript + Vite frontend

## Context

The first frontend was hand-written vanilla JavaScript with no build step. The library grew virtualised lists, column-header filter popovers, live job status, accessible tooltips and routing. Each of those is a solved problem with maintained accessible components, and the hand-rolled versions cost more to keep correct than they save in tooling.

## Decision

1. The frontend is a React 19 and TypeScript (strict) single-page app in `frontend/`, built with Vite. All dependencies are pinned exactly in `frontend/package-lock.json`.
2. Routing uses react-router, server state and job polling use TanStack Query, long lists use TanStack Virtual, and popovers, tooltips, dialogs and checkboxes use Radix UI primitives styled with our own CSS. There is no CSS framework, no external font and no CDN; icons are our own inline SVG components.
3. `vite build` writes hashed assets to `src/saber_tooth/web/`. Only the README of that folder is tracked. FastAPI serves `/assets/*` with `immutable` long-lived caching and `index.html` with `no-cache`.
4. The Docker image builds the bundle in a pinned `node` stage and copies the output into the final image; the Python stages and their cached layers are unchanged.
5. The visual rules of [ADR 0001](0001-vanilla-only-visuals.md) concern generated maps and do not change.

## Consequences

1. A Node toolchain is needed to work on the UI; running the service from a source checkout needs `task st:web:build` first, or `task st:web:dev` against a running API.
2. A source checkout without a build serves no frontend; the API and MCP routes work without it.
3. Frontend dependencies are a new supply-chain surface; the lockfile pins them and `npm audit` runs in the quality gate.
4. Component and hook tests run in Vitest with jsdom; the old `node:test` suites are removed.
