import { act, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { useJobRunner } from "../src/api/jobs";
import type { JobView } from "../src/api/types";
import { AnnouncerProvider } from "../src/components/Announcer";
import { JobToasts } from "../src/components/JobToasts";
import { mockFetch, toasts } from "./helpers";

beforeEach(() => {
  id = "j1";
  vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

const advance = (ms: number) => act(async () => void (await vi.advanceTimersByTimeAsync(ms)));
const closeToast = () => fireEvent.click(toasts().getByRole("button", { name: "Dismiss" }));

function Harness() {
  const runner = useJobRunner("Fix Song");
  return (
    <button type="button" onClick={() => void runner.run(async () => ({ job: "j1" }))}>
      go
    </button>
  );
}

function mountPage() {
  const router = createMemoryRouter([{ path: "/", element: <Harness /> }]);
  render(
    <AnnouncerProvider>
      <RouterProvider router={router} />
    </AnnouncerProvider>,
  );
}

function mountWatcher() {
  id = "w1"; // the page tests leave j1 marked as settled
  const client = new QueryClient();
  const router = createMemoryRouter([
    {
      path: "/",
      element: (
        <QueryClientProvider client={client}>
          <JobToasts />
        </QueryClientProvider>
      ),
    },
  ]);
  render(
    <AnnouncerProvider>
      <RouterProvider router={router} />
    </AnnouncerProvider>,
  );
}

let id = "j1";
const view = (status: JobView["status"], progress: string | null): JobView => ({
  id,
  kind: "fix",
  status,
  map_id: "m1",
  title: "Song",
  map_exists: true,
  created_at: "2026-10-29T10:00:00Z",
  started_at: null,
  updated_at: "2026-10-29T10:00:00Z",
  progress,
  progress_at: null,
  error: null,
  position: null,
  cancel_requested: false,
});

/** A server whose one job reports a new progress text on every poll until `finish` is set. */
function server() {
  const s = { n: 0, finish: false };
  mockFetch((url) => {
    if (url.pathname === `/api/jobs/${id}`) {
      s.n += 1;
      return s.finish
        ? { ...view("done", null), result: {} }
        : view("running", `round ${s.n} of 9`);
    }
    if (url.pathname === "/api/jobs") {
      s.n += 1;
      return s.finish
        ? { running: [], queued: [], recent: [view("done", null)] }
        : { running: [view("running", `round ${s.n} of 9`)], queued: [], recent: [] };
    }
    return {};
  });
  return s;
}

describe.each([
  ["page-started job", mountPage, async () => fireEvent.click(screen.getByText("go"))],
  ["list watcher", mountWatcher, async () => undefined],
])("running toast of a %s", (_name, mount, start) => {
  test("stays gone after the X while progress keeps changing; the outcome still shows", async () => {
    const s = server();
    mount();
    await start();
    await advance(2500);
    expect(toasts().getByText("Fix Song", { exact: false })).toBeTruthy();
    closeToast();
    expect(document.querySelector(".toast-stack .toast, .toast-stack .alert")).toBeNull();
    const before = s.n;
    await advance(12_000);
    expect(s.n).toBeGreaterThan(before + 3);
    expect(document.querySelector(".toast-stack")?.textContent).toBe("");
    s.finish = true;
    await advance(4000);
    expect(toasts().getByText("Done")).toBeTruthy();
    await advance(3100);
    expect(document.querySelector(".toast-stack")?.textContent).toBe("");
  });

  test("closes by itself after 3 s, does not return on the next poll, outcome still shows", async () => {
    const s = server();
    mount();
    await start();
    await advance(2500);
    expect(document.querySelector(".toast-stack")?.textContent).toContain("Fix");
    await advance(1500);
    expect(document.querySelector(".toast-stack")?.textContent).toBe("");
    await advance(12_000);
    expect(document.querySelector(".toast-stack")?.textContent).toBe("");
    s.finish = true;
    await advance(4000);
    expect(toasts().getByText("Done")).toBeTruthy();
  });
});
