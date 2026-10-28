# Task 13: VR Library screen

`/vr` shows the library as large cards: cover, title, status chip, levels, length, and the actions Preview, Fix and Open (or Open fixed copy). Five preset toggles sit above (Needs fix, Missing levels, Not scanned, Fixed copies, Expert+) and a four-way sort; there is no text search. The presets map onto the existing library query (`LibraryState`, `apiParams`): Needs fix is `status=error,warn`, Missing levels is `status=incomplete` (a map that was never scanned and lacks a level, `store_maps.py:81`), Not scanned is `status=unscanned`, Expert+ is `level=ExpertPlus`; status presets combine as OR, Expert+ narrows them. The API has no filter for fixed copies, so that preset is applied in the browser to the loaded cards: a fixed copy has `original_id`. The state lives in the address (`?p=needs-fix,expert-plus&sort=errors`), so a reload or a shared link restores it. More cards load when the end of the list scrolls into view.

**Files:**

- Create: `frontend/tests/vrhelpers.tsx`
- Create: `frontend/src/vr/presets.ts`
- Create: `frontend/src/vr/VrNav.tsx`
- Create: `frontend/src/vr/useNearEnd.ts`
- Create: `frontend/src/vr/VrCard.tsx`
- Create: `frontend/src/vr/VrLibraryPage.tsx`
- Modify: `frontend/src/styles/vr.css` (append)
- Modify: `frontend/src/vr/README.md` (append)
- Test: `frontend/tests/vrpresets.test.ts`, `frontend/tests/vrlibrary.test.tsx`

**Interfaces:**

Consumes: `useLibrary(state: LibraryState)`, `useLiveRows(items: MapItem[])` (`api/queries.ts`); `useFix(item: MapItem, name: string): () => Promise<void>` (`api/fix.ts`); `FixOutcomes` (`components/FixOutcomes.tsx`); `Cover`, `LevelChips`, `StatusChip` (`components/Chips.tsx`); `PreviewButton({ src, title, start })` (`components/PreviewButton.tsx`); `SpecAlert`, `errorToAlert`; `mapName`, `STATUS_ORDER` (`lib/status.ts`); `formatDuration` (`lib/format.ts`); `DEFAULT_STATE`, `LibraryState` (`lib/urlstate.ts`); `useDocumentTitle` (`lib/hooks.ts`); `item`, `mockFetch` (`tests/helpers.tsx`).

Produces:

1. `vr/presets.ts`: `VR_PRESETS` (`key`, `label`, `help`), `type VrPreset`, `VR_SORTS` (`key`, `label`, `sort`, `order`), `type VrSort`, `interface VrView { presets: VrPreset[]; sort: VrSort }`, `parseVrView(search: string): VrView`, `encodeVrView(view: VrView): URLSearchParams`, `togglePreset(view: VrView, key: VrPreset): VrView`, `vrState(view: VrView): LibraryState`, `isFixedCopy(item: Pick<MapItem, "original_id">): boolean`.
2. `vr/VrNav.tsx`: `VrNav({ active }: { active: "library" | "beatsaver" })`, two large links to `/vr` and `/vr/beatsaver`.
3. `vr/useNearEnd.ts`: `useNearEnd(onNear: () => void, enabled: boolean): RefObject<HTMLDivElement | null>`; attach the ref to an end sentinel; `onNear` runs when it comes within 600 px of view; without `IntersectionObserver` nothing happens.
4. `vr/VrCard.tsx`: `VrCard({ item }: { item: MapItem })`.
5. `vr/VrLibraryPage.tsx`: `VrLibraryPage()`.
6. `tests/vrhelpers.tsx`: `renderVr(url: string, route: string, element: ReactElement)` (query client, tooltips, announcer, memory router with `element` at `route` and a `Where` probe showing path and query as `data-testid="where"`), `stubObserver(): { fire: () => void }`.

- [ ] **Step 1: Write the test helpers**

Create `frontend/tests/vrhelpers.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { vi } from "vitest";
import { makeQueryClient } from "../src/App";
import { AnnouncerProvider } from "../src/components/Announcer";
import { TipProvider } from "../src/components/Tip";

function Where() {
  const { pathname, search } = useLocation();
  return <span data-testid="where">{pathname + search}</span>;
}

/** Render a VR screen at `url`, mounted on the route pattern `route`. */
export function renderVr(url: string, route: string, element: ReactElement) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <TipProvider delayDuration={0}>
        <AnnouncerProvider>
          <MemoryRouter initialEntries={[url]}>
            <Routes>
              <Route path={route} element={element} />
              <Route path="*" element={<span>elsewhere</span>} />
            </Routes>
            <Where />
          </MemoryRouter>
        </AnnouncerProvider>
      </TipProvider>
    </QueryClientProvider>,
  );
}

/** Stand in for IntersectionObserver; `fire()` reports the newest observer's target as visible. */
export function stubObserver() {
  const callbacks: IntersectionObserverCallback[] = [];
  class Stub {
    constructor(callback: IntersectionObserverCallback) {
      callbacks.push(callback);
    }
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal("IntersectionObserver", Stub);
  return {
    fire: () =>
      callbacks.at(-1)?.(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      ),
  };
}
```

- [ ] **Step 2: Write the failing presets test**

Create `frontend/tests/vrpresets.test.ts`:

```ts
import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { apiParams, DEFAULT_STATE } from "../src/lib/urlstate";
import {
  VR_PRESETS,
  VR_SORTS,
  encodeVrView,
  isFixedCopy,
  parseVrView,
  togglePreset,
  vrState,
  type VrView,
} from "../src/vr/presets";

const view = (presets: VrView["presets"], sort: VrView["sort"] = "title"): VrView => ({
  presets,
  sort,
});

describe("vrState", () => {
  test("no preset is the plain library query", () => {
    expect(vrState(view([]))).toEqual({ ...DEFAULT_STATE, sort: "title", order: "asc" });
  });

  test.each([
    [["needs-fix"], ["error", "warn"], []],
    [["missing-levels"], ["incomplete"], []],
    [["unscanned"], ["unscanned"], []],
    [["expert-plus"], [], ["ExpertPlus"]],
    [["unscanned", "needs-fix"], ["error", "warn", "unscanned"], []],
    [["needs-fix", "expert-plus"], ["error", "warn"], ["ExpertPlus"]],
    [["fixed"], [], []],
  ] as const)("%j builds status %j and level %j", (presets, status, level) => {
    const state = vrState(view([...presets]));
    expect(state.status).toEqual(status);
    expect(state.level).toEqual(level);
  });

  test.each([
    ["title", "title", "asc"],
    ["errors", "errors", "desc"],
    ["recent", "scanned_at", "desc"],
    ["length", "duration", "desc"],
  ] as const)("sort %s asks the API for %s %s", (key, sort, order) => {
    const params = apiParams(vrState(view([], key)), 0, 40);
    expect(params.get("sort")).toBe(sort);
    expect(params.get("order")).toBe(order);
  });

  test("a query never carries a text search", () => {
    for (const p of VR_PRESETS) expect(vrState(view([p.key])).q).toBe("");
  });
});

describe("parseVrView and encodeVrView", () => {
  test("round trip", () => {
    const v = view(["needs-fix", "expert-plus"], "errors");
    expect(encodeVrView(v).toString()).toBe("p=needs-fix%2Cexpert-plus&sort=errors");
    expect(parseVrView(encodeVrView(v).toString())).toEqual(v);
  });

  test("the defaults leave the address clean", () => {
    expect(encodeVrView(view([])).toString()).toBe("");
  });

  test("unknown presets and sorts are ignored, known ones come out in the fixed order", () => {
    expect(parseVrView("p=expert-plus,bogus,needs-fix,needs-fix&sort=nope")).toEqual(
      view(["needs-fix", "expert-plus"], "title"),
    );
    expect(parseVrView("")).toEqual(view([]));
  });

  test("arbitrary addresses parse to a valid view", () => {
    fc.assert(
      fc.property(fc.string(), (search) => {
        const v = parseVrView(search);
        expect(VR_SORTS.map((s) => s.key)).toContain(v.sort);
        expect(new Set(v.presets).size).toBe(v.presets.length);
        expect(v.presets.every((k) => VR_PRESETS.some((p) => p.key === k))).toBe(true);
        expect(parseVrView(encodeVrView(v).toString())).toEqual(v);
      }),
    );
  });
});

describe("togglePreset and isFixedCopy", () => {
  test("toggles one preset on and off and keeps the sort", () => {
    const on = togglePreset(view([], "length"), "fixed");
    expect(on).toEqual(view(["fixed"], "length"));
    expect(togglePreset(on, "fixed")).toEqual(view([], "length"));
  });

  test("a fixed copy is a map with an original", () => {
    expect(isFixedCopy({ original_id: "abc" })).toBe(true);
    expect(isFixedCopy({ original_id: null })).toBe(false);
    expect(isFixedCopy({})).toBe(false);
  });
});
```

Continued in [task-13b.md](task-13b.md).
