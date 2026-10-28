# Task 16: MapPage wiring

**Files:**

- Modify: `frontend/src/pages/MapPage.tsx` (two anchored edits)
- Test: `frontend/tests/cropwiring.test.tsx`

**Interfaces:**

Consumes: `CropPanel({ mapId, busy })` (Task 15); in `MapPage`, `id` from `useParams`, `map.data`, and `running` (`map.data?.job != null || scan.busy || apply.busy`).

Produces: the panel on `/maps/:id` for every readable map, between the job outcomes and the approve alerts.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/cropwiring.test.tsx`:

```tsx
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { cropApi } from "./crophelpers";
import { renderApp } from "./helpers";

describe("crop panel on the map page", () => {
  test("is offered on a map, and the timeline loads only when it is opened", async () => {
    const { calls } = cropApi();
    renderApp("/maps/id0000000001");
    const toggle = await screen.findByRole("button", { name: /Crop to 1 or 2 minutes/ });
    expect(calls.some((u) => u.pathname.endsWith("/timeline"))).toBe(false);
    await userEvent.setup().click(toggle);
    expect(await screen.findByRole("slider", { name: "Crop end" })).toBeInTheDocument();
  });

  test("Create is disabled while a job runs on the map", async () => {
    cropApi({ map: { status: "scanning", job: { id: "j", kind: "scan", status: "running" } } });
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Crop to 1 or 2 minutes/ }));
    await screen.findByRole("slider", { name: "Crop end" });
    expect(screen.getByRole("button", { name: "Create cropped map" })).toBeDisabled();
  });

  test("is not offered on an unreadable map", async () => {
    cropApi({ map: { status: "unreadable", parse_error: "bad json" } });
    renderApp("/maps/id0000000001");
    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByRole("button", { name: /Crop to 1 or 2 minutes/ })).toBeNull();
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx --prefix frontend vitest run --root frontend tests/cropwiring.test.tsx`
Expected: FAIL: the toggle button is not found on the map page.

- [ ] **Step 3: Implement**

In `frontend/src/pages/MapPage.tsx` add the import directly after `import { FixedCopyLink } from "../components/FixedCopyLink";`:

```tsx
import { CropPanel } from "../components/CropPanel";
```

and replace

```tsx
        onRetry={() => void scan.run(() => scanMap(id)).then(refresh)}
      />
```

(the `onRetry` of the scan `JobOutcome`; it is the only place that string is followed by a closing `/>` line) with

```tsx
        onRetry={() => void scan.run(() => scanMap(id)).then(refresh)}
      />
      {map.data && map.data.status !== "unreadable" && (
        <CropPanel key={id} mapId={id} busy={running} />
      )}
```

- [ ] **Step 4: Run to pass, then the map-page suites**

Run: `npx --prefix frontend vitest run --root frontend tests/cropwiring.test.tsx tests/pages.test.tsx tests/proposals.test.tsx tests/fixes.test.tsx tests/delete.test.tsx tests/fixedcopy.test.tsx tests/skeletons.test.tsx tests/timeout.test.tsx`
Expected: all pass. The new panel is collapsed, so these suites see no new request; if one fails on a duplicate button name or heading count, fix the panel markup, not the older test.

- [ ] **Step 5: Gates**

Run: `npm --prefix frontend run typecheck`
Expected: no errors.
Run: `npm --prefix frontend run lint`
Expected: no warnings.
Run: `npx --prefix frontend prettier --config .crepidoma/configs/.prettierrc --check frontend/tests/cropwiring.test.tsx`
Expected: pass. Do not run prettier over `MapPage.tsx`: it carries another lane's uncommitted edits.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: crop panel on the map page"` (subagents never commit).
