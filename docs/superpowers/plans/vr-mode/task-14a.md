# Task 14: VR Map screen

`/vr/maps/:id` shows one map for fixing, deleting and cropping: header, status, banners, a large Fix, Delete behind a confirm, and the crop panel from the crop-highlight plan ([task-15a](../crop-highlight/task-15a.md), [task-15b](../crop-highlight/task-15b.md)): the 1 min / 2 min switch, the NPS chart, Reset to suggestion and Create cropped map. The panel already steps by keyboard and drag; this task adds an opt-in `steps` prop that shows four large buttons wired to the panel's own `onStep(edge, dir, jump)`: Previous section and Next section move the start, End earlier and End later move the end by one allowed point. No new stepping logic exists: `stepStart` and `stepEnd` (`lib/crop.ts`) already stay on the current point at the first and last allowed point, and a new test pins that. Map review (proposals, Approve, Apply) and Scan are not part of the VR layout.

This task needs the crop panel merged first: the crop-highlight lane builds `CropPanel.tsx`, `crophelpers.tsx` (`TIMELINE`, `cropApi`, `renderPanel`) and `NpsChart.tsx`; run it after that lane lands.

**Files:**

- Create: `frontend/src/vr/CropSteps.tsx`
- Modify: `frontend/src/components/CropPanel.tsx` (the `steps` prop, four anchored edits)
- Create: `frontend/src/vr/VrMapPage.tsx`
- Modify: `frontend/src/styles/vr.css` (append)
- Modify: `frontend/src/vr/README.md` (append)
- Test: `frontend/tests/vrcrop.test.tsx`, `frontend/tests/vrmap.test.tsx`

**Interfaces:**

Consumes: `CropPanel({ mapId, busy })` and `Edge` (`components/CropPanel.tsx`, `components/NpsChart.tsx`); `TIMELINE`, `cropApi`, `renderPanel` (`tests/crophelpers.tsx`); `useMap`, `useLiveRows` (`api/queries.ts`); `useFix`; `deleteMap`, `ApiError`, `errorMessage` (`api/client.ts`); `ConfirmDialog`; `FixedCopyLink`, `FixedCopyOf`; `FixOutcomes`; `Cover`, `LevelChips`, `StatusChip`, `Tempo`; `MapHeadSkeleton` (`components/Skeletons.tsx`); `NotFoundPage` (`pages/NotFoundPage.tsx`); `useAnnounce`; `TIPS` (`lib/tips.ts`); `isCleanCopy`, `mapName` (`lib/status.ts`); `formatEnvironment`; `renderVr` (Task 13).

Produces:

1. `CropPanel({ mapId, busy, steps }: { mapId: string; busy: boolean; steps?: boolean })`: `steps` defaults to `false`; when true the editor shows `CropSteps` under the chart.
2. `vr/CropSteps.tsx`: `CropSteps({ onStep }: { onStep: (edge: Edge, dir: 1 | -1, jump: boolean) => void })`: a group named "Move the crop" with the buttons Previous section, Next section, End earlier, End later, each with its help as text under it.
3. `vr/VrMapPage.tsx`: `VrMapPage()`.

- [ ] **Step 1: Write the failing crop-steps test**

Create `frontend/tests/vrcrop.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { cropApi, renderPanel } from "./crophelpers";

const TOGGLE = /Crop to 1 or 2 minutes/;

async function setup(props: { steps?: boolean } = { steps: true }) {
  const api = cropApi();
  renderPanel(<CropPanel mapId="id0000000001" busy={false} {...props} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: TOGGLE }));
  await screen.findByRole("slider", { name: "Crop end" });
  return { ...api, user };
}

const press = (user: ReturnType<typeof userEvent.setup>, name: string) =>
  user.click(screen.getByRole("button", { name }));

async function created(user: ReturnType<typeof userEvent.setup>, posts: { body: unknown }[]) {
  await press(user, "Create cropped map");
  await waitFor(() => expect(posts).toHaveLength(1));
  return posts[0]!.body;
}

describe("CropPanel steps", () => {
  test("the step buttons are off unless asked for", async () => {
    await setup({});
    expect(screen.queryByRole("group", { name: "Move the crop" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Next section" })).toBeNull();
  });

  test("four large step buttons appear, each with its help as text", async () => {
    await setup();
    const group = screen.getByRole("group", { name: "Move the crop" });
    for (const name of ["Previous section", "Next section", "End earlier", "End later"]) {
      expect(screen.getByRole("button", { name })).toBeEnabled();
    }
    expect(group).toHaveTextContent("Move the end to the previous allowed point.");
    expect(group).toHaveTextContent("Move the end to the next allowed point.");
  });

  test("End earlier and End later walk the allowed ends one point at a time", async () => {
    const { user } = await setup();
    expect(screen.getByText(/^Length 1:04\.0/)).toBeInTheDocument();
    await press(user, "End earlier");
    expect(screen.getByText(/^Length 0:58\.0/)).toHaveClass("crop-amber");
    await press(user, "End earlier");
    expect(screen.getByText(/^Length 0:56\.0/)).toBeInTheDocument();
    await press(user, "End later");
    await press(user, "End later");
    expect(screen.getByText(/^Length 1:04\.0/)).not.toHaveClass("crop-amber");
    await press(user, "End later");
    expect(screen.getByText(/^Length 1:06\.0/)).toBeInTheDocument();
  });

  test("Next section moves the start, re-picks the end and Create posts the window", async () => {
    const { user, posts } = await setup();
    await press(user, "Next section");
    expect(screen.getByText(/^Length 1:04\.0/)).toHaveTextContent("phrase line");
    expect(await created(user, posts)).toEqual({ start_beat: 128, end_beat: 256 });
  });

  test("step buttons stay put at the first and last allowed point", async () => {
    const { user, posts } = await setup();
    await press(user, "Previous section");
    expect(screen.getByText(/^Length 1:04\.0/)).toBeInTheDocument();
    for (let i = 0; i < 4; i++) await press(user, "End later");
    for (let i = 0; i < 6; i++) await press(user, "End earlier");
    expect(screen.getByText(/^Length 0:56\.0/)).toBeInTheDocument();
    await press(user, "Reset to suggestion");
    await press(user, "Next section");
    await press(user, "Next section");
    await press(user, "Next section");
    expect(await created(user, posts)).toEqual({ start_beat: 128, end_beat: 256 });
  });

  test("Previous section returns to the first start", async () => {
    const { user, posts } = await setup();
    await press(user, "Next section");
    await press(user, "Previous section");
    expect(await created(user, posts)).toMatchObject({ start_beat: 0 });
  });
});
```

- [ ] **Step 2: Write the failing page test**

Create `frontend/tests/vrmap.test.tsx`:

```tsx
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { MapItem } from "../src/api/types";
import { TIPS } from "../src/lib/tips";
import { VrMapPage } from "../src/vr/VrMapPage";
import { TIMELINE } from "./crophelpers";
import { item, mockFetch } from "./helpers";
import { renderVr } from "./vrhelpers";

const ID = "id0000000001";

function mapApi(patch: Partial<MapItem> = {}, map: unknown = item(1, patch)) {
  return mockFetch((url, init) => {
    if (init?.method === "DELETE") return { deleted: "Folder 1" };
    if (init?.method === "POST") return { job: "j" };
    if (url.pathname === `/api/maps/${ID}`) return map;
    if (url.pathname === `/api/maps/${ID}/timeline`) return TIMELINE;
    if (url.pathname.startsWith("/api/jobs/")) {
      return { id: "j", kind: "fix", status: "running", error: null, result: null };
    }
    return {};
  });
}

const show = () => renderVr(`/vr/maps/${ID}`, "/vr/maps/:id", <VrMapPage />);
const sent = (fn: ReturnType<typeof mapApi>["fn"], method: string, path: string) =>
  fn.mock.calls.some(([url, init]) => String(url) === path && init?.method === method);

describe("VR map screen", () => {
  test("shows the header, status and a way back to the VR library", async () => {
    mapApi({ status: "error", errors: 3, mapper: "Ada" });
    show();
    expect(await screen.findByRole("heading", { name: "Song 1" })).toBeInTheDocument();
    expect(screen.getByText(/Ada/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "3 errors" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Library/ })).toHaveAttribute("href", "/vr");
  });

  test("a large Fix starts the fix job and explains itself as text", async () => {
    const { fn } = mapApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Fix" }));
    await waitFor(() => expect(sent(fn, "POST", `/api/maps/${ID}/fix`)).toBe(true));
    expect(screen.getByText(TIPS.fix)).toBeInTheDocument();
  });

  test("a fixed copy needs no Fix and links back to its original", async () => {
    mapApi({
      status: "ok",
      folder: "Folder 1 [saber-tooth]",
      original_id: "id0000000009",
      original_folder: "Folder 1",
    });
    show();
    expect(await screen.findByText("Fixed copy of")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Fix" })).toBeNull();
  });

  test("Fix and Delete are off while a job runs on the map", async () => {
    mapApi({ job: { id: "j", kind: "scan", status: "running" }, status: "scanning" });
    show();
    expect(await screen.findByRole("button", { name: "Fix" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
  });

  test("Delete asks first and Cancel deletes nothing", async () => {
    const { fn } = mapApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete permanently?" });
    expect(dialog).toHaveTextContent('"Folder 1" is removed from disk and cannot be undone.');
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(sent(fn, "DELETE", `/api/maps/${ID}`)).toBe(false);
    expect(screen.getByText(TIPS.delete)).toBeInTheDocument();
  });

  test("confirming Delete removes the map and returns to the VR library", async () => {
    const { fn } = mapApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete permanently?" });
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(sent(fn, "DELETE", `/api/maps/${ID}`)).toBe(true));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/vr$/));
  });

  test("the crop panel is there with the step buttons", async () => {
    mapApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: /Crop to 1 or 2 minutes/ }));
    expect(await screen.findByRole("radio", { name: "1 min" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "2 min" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Move the crop" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create cropped map" })).toBeEnabled();
  });

  test("an unknown map says so", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ error: "no such map" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }),
    );
    show();
    expect(await screen.findByText("Map not found")).toBeInTheDocument();
  });

  test("a map that cannot be loaded shows an alert", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ error: "bad" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
    );
    show();
    expect(await screen.findByText("Could not load the map")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run them to see them fail**

Run: `npx --prefix frontend vitest run --root frontend tests/vrcrop.test.tsx tests/vrmap.test.tsx`
Expected: FAIL: `Failed to resolve import "../src/vr/VrMapPage"` (and no `steps` buttons in the panel).

Continued in [task-14b.md](task-14b.md).
