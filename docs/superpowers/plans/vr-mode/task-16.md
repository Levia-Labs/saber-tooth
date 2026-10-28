# Task 16: Router wiring for the three VR screens

The three screens become lazy routes under the existing `Shell`, built the way the other pages are (`lazyRoute`, one `errorElement` each). `frontend/tests/setup.ts` pre-compiles lazy pages outside the test timers, so the three VR pages join that list. The server side already serves `/vr`, `/vr/maps/{id}` and `/vr/beatsaver` on reload (Task 7). `Shell` does not mount `VrModeProvider` yet; Task 17 does, so this task changes no behaviour for desktop routes.

**Files:**

- Modify: `frontend/src/App.tsx` (three lazy imports, three routes)
- Modify: `frontend/tests/setup.ts` (three pre-compiled imports)
- Modify: `frontend/src/vr/README.md` (append)
- Test: `frontend/tests/vrroutes.test.tsx`

**Interfaces:**

Consumes: `lazyRoute`, `routes`, `RouteError`, `NotFoundPage` (existing); `VrLibraryPage`, `VrMapPage`, `VrBeatSaverPage` (Tasks 13 to 15); `renderApp(url)`, `item`, `mockFetch` (`tests/helpers.tsx`); `bsMap`, `page`, `SEEDED` (`tests/bshelpers.tsx`).

Produces: `routes` gains `/vr`, `/vr/maps/:id` and `/vr/beatsaver`; an unknown `/vr/...` path still reaches the existing `*` route.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/vrroutes.test.tsx`:

```tsx
import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { bsMap, page, SEEDED } from "./bshelpers";
import { item, mockFetch, renderApp } from "./helpers";

function api() {
  return mockFetch((url) => {
    if (url.pathname === "/api/maps") return { items: [item(1)], total: 1, offset: 0, limit: 40 };
    if (url.pathname === "/api/maps/id0000000001") return item(1);
    if (url.pathname === "/api/beatsaver/search") return page([bsMap(1)]);
    if (url.pathname === "/api/beatsaver/presets") return [SEEDED];
    return {};
  });
}

describe("VR routes", () => {
  test("/vr is the VR library inside the shell", async () => {
    api();
    renderApp("/vr");
    expect(await screen.findByRole("heading", { name: "Library", level: 1 })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Song 1" })).toBeInTheDocument();
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fix Song 1" })).toBeInTheDocument();
  });

  test("/vr/maps/:id is the VR map screen", async () => {
    api();
    renderApp("/vr/maps/id0000000001");
    expect(await screen.findByRole("heading", { name: "Song 1", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ })).toBeInTheDocument();
  });

  test("/vr/beatsaver is the VR BeatSaver screen", async () => {
    api();
    renderApp("/vr/beatsaver");
    expect(await screen.findByRole("heading", { name: "BeatSaver", level: 1 })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Download Song 1" })).toBeInTheDocument();
  });

  test("an unknown VR path still reaches the not-found page", async () => {
    api();
    renderApp("/vr/nope");
    expect(await screen.findByText(/not found/i)).toBeInTheDocument();
  });

  test("the desktop routes are unchanged", async () => {
    api();
    renderApp("/beatsaver");
    expect(
      await screen.findByRole("navigation", { name: "BeatSaver sections" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("radiogroup", { name: "Sort by" })).toBeNull();
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx --prefix frontend vitest run --root frontend tests/vrroutes.test.tsx`
Expected: FAIL: the first three tests time out waiting for the headings (`/vr` falls into the not-found route).

- [ ] **Step 3: Implement**

In `frontend/src/App.tsx`, add after the `NewPage` lazy import:

```tsx
const VrLibraryPage = lazyRoute(() =>
  import("./vr/VrLibraryPage").then((m) => ({ default: m.VrLibraryPage })),
);
const VrMapPage = lazyRoute(() => import("./vr/VrMapPage").then((m) => ({ default: m.VrMapPage })));
const VrBeatSaverPage = lazyRoute(() =>
  import("./vr/VrBeatSaverPage").then((m) => ({ default: m.VrBeatSaverPage })),
);
```

Add three routes before `{ path: "*", ... }`:

```tsx
      { path: "/vr", element: <VrLibraryPage />, errorElement: <RouteError /> },
      { path: "/vr/maps/:id", element: <VrMapPage />, errorElement: <RouteError /> },
      { path: "/vr/beatsaver", element: <VrBeatSaverPage />, errorElement: <RouteError /> },
```

In `frontend/tests/setup.ts`, add to the `Promise.all([...])` list after `import("../src/pages/NewPage"),`:

```ts
  import("../src/vr/VrLibraryPage"),
  import("../src/vr/VrMapPage"),
  import("../src/vr/VrBeatSaverPage"),
```

Append to `frontend/src/vr/README.md`:

```markdown
7. Routes: `/vr`, `/vr/maps/:id` and `/vr/beatsaver` are lazy routes in `App.tsx`; the server answers them with `index.html` on reload.
```

- [ ] **Step 4: Run it to see it pass**

Run: `npx --prefix frontend vitest run --root frontend tests/vrroutes.test.tsx tests/lazyRoute.test.tsx tests/appStable.test.tsx tests/pages.test.tsx`
Expected: PASS.

- [ ] **Step 5: Type check and lint**

Run: `npm --prefix frontend run typecheck` then `npm --prefix frontend run lint`
Expected: both exit 0.

- [ ] **Step 6: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): routes for the three VR screens" frontend/src/App.tsx frontend/tests/setup.ts frontend/src/vr/README.md frontend/tests/vrroutes.test.tsx`
