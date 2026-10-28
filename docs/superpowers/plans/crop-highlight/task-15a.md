# Task 15: CropPanel with snapping, keyboard and states

The panel is a disclosure: collapsed until the user opens it, and the timeline is fetched only then, so the map page costs nothing for users who never crop and existing map-page tests see no new request. It has its own job runner (`useJobRunner("Crop")`), so progress, success and failure use the keyed banners of `Announcer.tsx`; the finished job also leaves an alert with a link to the new folder.

**Files:**

- Create: `frontend/src/components/CropPanel.tsx`
- Modify: `frontend/src/styles/crop.css` (append)
- Modify: `frontend/tests/crophelpers.tsx` (append `renderPanel`, `cropApi`)
- Test: `frontend/tests/croppanel.test.tsx`

**Interfaces:**

Consumes: `NpsChart`, `Edge` (Task 14); everything in `lib/crop.ts` (Task 13); `useTimeline` (Task 13); `cropMap`; `useJobRunner(label)` returning `{state, busy, error, job, run(start)}` (`api/jobs.ts`); `ActionButton({icon, label, tip, text, variant, disabled, onClick})` (`components/Buttons.tsx`); `Alert`, `SpecAlert` (`components/Alert.tsx`); `errorToAlert`, `toAlert` (`lib/alerts.ts`); `Icon` names `expand`, `collapse`, `apply`, `reset`.

Produces (`components/CropPanel.tsx`): `CropPanel({ mapId, busy }: { mapId: string; busy: boolean }): JSX.Element`. `busy` is true while a job runs on the map; Create is disabled while `busy` or the panel's own crop job runs.

Produces (`tests/crophelpers.tsx`): `renderPanel(ui)` (query client, tooltips, announcer and memory router around `ui`); `cropApi(options?: { timeline?: unknown; jobStatus?: string; jobError?: string | null; map?: Partial<MapItem> })` stubbing fetch for `/api/maps/id0000000001`, its `/proposals`, `/timeline`, `POST` anything (answers `{job: "jc"}`, recorded in `posts`) and `/api/jobs/jc`, returning `{ posts, calls, fn }`.

- [ ] **Step 1: Write the failing test**

Append to `frontend/tests/crophelpers.tsx` (put the new imports at the top of the file):

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { makeQueryClient } from "../src/App";
import { AnnouncerProvider } from "../src/components/Announcer";
import { TipProvider } from "../src/components/Tip";
import type { MapItem } from "../src/api/types";
import { item, mockFetch } from "./helpers";

export function renderPanel(ui: ReactElement) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <TipProvider delayDuration={0}>
        <AnnouncerProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </AnnouncerProvider>
      </TipProvider>
    </QueryClientProvider>,
  );
}

interface ApiOptions {
  timeline?: unknown;
  jobStatus?: string;
  jobError?: string | null;
  map?: Partial<MapItem>;
}

export function cropApi(options: ApiOptions = {}) {
  const posts: { path: string; body: unknown }[] = [];
  const mock = mockFetch((url, init) => {
    if (init?.method === "POST") {
      posts.push({ path: url.pathname, body: JSON.parse(String(init.body ?? "{}")) });
      return { job: "jc" };
    }
    if (url.pathname === "/api/maps/id0000000001") return item(1, options.map);
    if (url.pathname === "/api/maps/id0000000001/proposals") return [];
    if (url.pathname === "/api/maps/id0000000001/timeline") return options.timeline ?? TIMELINE;
    if (url.pathname === "/api/jobs/j") {
      return { id: "j", kind: "scan", status: "running", error: null, result: null };
    }
    if (url.pathname === "/api/jobs/jc") {
      return {
        id: "jc",
        kind: "crop",
        status: options.jobStatus ?? "done",
        error: options.jobError ?? null,
        result: {
          map_id: "id0000000001",
          folder: "Folder 1 [1 min]",
          cropped_id: "id0000000099",
          label: "1 min",
          start_beat: 0,
          end_beat: 128,
          length_s: 64,
        },
      };
    }
    return { items: [item(1)], total: 1, offset: 0, limit: 40 };
  });
  return { ...mock, posts };
}
```

Create `frontend/tests/croppanel.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { TIMELINE, cropApi, renderPanel } from "./crophelpers";

const P120 = TIMELINE.lengths["120"];

async function openPanel(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ }));
  await screen.findByRole("slider", { name: "Crop end" });
}

function setup(options = {}, busy = false) {
  const api = cropApi(options);
  renderPanel(<CropPanel mapId="id0000000001" busy={busy} />);
  return { ...api, user: userEvent.setup() };
}

describe("CropPanel", () => {
  test("stays closed, and fetches nothing, until it is opened", async () => {
    const { calls, user } = setup();
    const toggle = screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(calls.some((u) => u.pathname.endsWith("/timeline"))).toBe(false);
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await screen.findByRole("slider", { name: "Crop start" });
  });

  test("shows a skeleton while the timeline loads", async () => {
    const slow = new Promise((resolve) => setTimeout(() => resolve(TIMELINE), 100));
    const { user } = setup({ timeline: slow });
    await user.click(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ }));
    expect(document.querySelector("[data-skeleton]")).not.toBeNull();
    await screen.findByRole("slider", { name: "Crop end" });
    expect(document.querySelector("[data-skeleton]")).toBeNull();
  });

  test("opens on the suggestion with its exact length", async () => {
    const { user } = setup();
    await openPanel(user);
    const readout = screen.getByText(/^Length 1:04\.0/);
    expect(readout).not.toHaveClass("crop-amber");
    expect(readout).toHaveTextContent("Both cuts are on section boundaries.");
    expect(screen.getByRole("button", { name: "Create cropped map" })).toBeEnabled();
  });

  test("the end steps to allowed points and the readout turns amber off a section end", async () => {
    const { user } = setup();
    await openPanel(user);
    screen.getByRole("slider", { name: "Crop end" }).focus();
    await user.keyboard("{ArrowLeft}");
    const readout = screen.getByText(/^Length 0:58\.0/);
    expect(readout).toHaveClass("crop-amber");
    expect(readout).toHaveTextContent("Ends on a bar line, not a section boundary.");
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    expect(screen.getByText(/^Length 1:04\.0/)).not.toHaveClass("crop-amber");
  });

  test("moving the start re-picks the end and Create posts the chosen beats", async () => {
    const { user, posts } = setup();
    await openPanel(user);
    screen.getByRole("slider", { name: "Crop start" }).focus();
    await user.keyboard("{ArrowRight}");
    const readout = screen.getByText(/^Length 1:04\.0/);
    expect(readout).toHaveTextContent("Ends on a phrase line, not a section boundary.");
    await user.click(screen.getByRole("button", { name: "Create cropped map" }));
    await waitFor(() =>
      expect(posts).toEqual([
        { path: "/api/maps/id0000000001/crop", body: { start_beat: 128, end_beat: 256 } },
      ]),
    );
  });

  test("Reset to suggestion appears after an edit and restores the suggestion", async () => {
    const { user } = setup();
    await openPanel(user);
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
    screen.getByRole("slider", { name: "Crop end" }).focus();
    await user.keyboard("{ArrowLeft}");
    await user.click(screen.getByRole("button", { name: /Reset to suggestion/ }));
    expect(screen.getByText(/^Length 1:04\.0/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
  });

  test("switching to 2 min keeps the start when it exists and re-picks the end", async () => {
    const { user } = setup();
    await openPanel(user);
    await user.click(screen.getByRole("radio", { name: "2 min" }));
    expect(screen.getByRole("radio", { name: "2 min" })).toBeChecked();
    expect(screen.getByText(/^Length 1:52\.0/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
  });

  test("switching to a length without the chosen start falls back to its suggestion", async () => {
    const { user } = setup();
    await openPanel(user);
    screen.getByRole("slider", { name: "Crop start" }).focus();
    await user.keyboard("{ArrowRight}");
    await user.click(screen.getByRole("radio", { name: "2 min" }));
    expect(screen.getByText(/^Length 1:52\.0/)).toBeInTheDocument();
  });

  test("a map without analysis says its sections come from the map only", async () => {
    const { user } = setup({ timeline: { ...TIMELINE, map_only: true } });
    await openPanel(user);
    expect(screen.getByText("Sections from map only")).toBeInTheDocument();
  });

  test("a length the song is too short for is disabled with the reason", async () => {
    const reason = "The song is 90 s long; a 2 min crop needs at least 132 s.";
    const short = {
      ...TIMELINE,
      lengths: { ...TIMELINE.lengths, "120": { ...P120, enabled: false, reason } },
    };
    const { user } = setup({ timeline: short });
    await openPanel(user);
    expect(screen.getByRole("radio", { name: "2 min" })).toBeDisabled();
    expect(screen.getByText(reason)).toBeInTheDocument();
  });

  test("a timeline that cannot be built shows a danger alert and nothing else breaks", async () => {
    const failing = new Response(JSON.stringify({ error: "no Standard difficulty has notes" }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    });
    const { user } = setup({ timeline: failing });
    await user.click(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ }));
    expect(await screen.findByText("Could not build the crop timeline")).toBeInTheDocument();
    expect(screen.getByText(/no Standard difficulty has notes/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ })).toBeEnabled();
  });

  test("a finished job links to the new folder", async () => {
    const { user } = setup();
    await openPanel(user);
    await user.click(screen.getByRole("button", { name: "Create cropped map" }));
    const link = await screen.findByRole("link", { name: "Open cropped map" });
    expect(link).toHaveAttribute("href", "/maps/id0000000099");
    expect(screen.getByText(/Written to Folder 1 \[1 min\]/)).toBeInTheDocument();
  });

  test("a failed job shows the reason", async () => {
    const { user } = setup({ jobStatus: "failed", jobError: "ffmpeg failed: bad input" });
    await openPanel(user);
    await user.click(screen.getByRole("button", { name: "Create cropped map" }));
    expect(await screen.findByText("Crop failed")).toBeInTheDocument();
    expect(screen.getByText(/ffmpeg failed: bad input/)).toBeInTheDocument();
  });

  test("Create is disabled while a job runs on the map", async () => {
    const { user } = setup({}, true);
    await openPanel(user);
    expect(screen.getByRole("button", { name: "Create cropped map" })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx --prefix frontend vitest run --root frontend tests/croppanel.test.tsx`
Expected: FAIL: `Failed to resolve import "../src/components/CropPanel"`.

Continued in [task-15b.md](task-15b.md).
