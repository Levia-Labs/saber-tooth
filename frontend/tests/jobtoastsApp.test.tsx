import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { JobLists, JobView } from "../src/api/types";
import { FACETS, item, mockFetch, renderApp, toasts } from "./helpers";

const view = (id: string, status: JobView["status"], extra: Partial<JobView> = {}): JobView => ({
  id,
  kind: "fix",
  status,
  map_id: "id0000000001",
  title: "Song 1",
  map_exists: true,
  created_at: "2026-10-29T10:00:00Z",
  started_at: null,
  updated_at: "2026-10-29T10:00:00Z",
  progress: null,
  progress_at: null,
  error: null,
  position: null,
  cancel_requested: false,
  ...extra,
});

const items = [item(1, { status: "error", errors: 2 })];

/** Library stubs plus a swappable `/api/jobs` answer. */
function api(initial: JobLists | Record<string, never>, extra?: (url: URL) => unknown) {
  const state = { jobs: initial as unknown };
  const mock = mockFetch((url, init) => {
    const own = extra?.(url);
    if (own !== undefined) return own;
    if (init?.method === "POST") return { job: "jf" };
    if (url.pathname === "/api/jobs") return state.jobs;
    if (url.pathname === "/api/maps/facets") return FACETS;
    return { items, total: items.length, offset: 0, limit: 40 };
  });
  return { ...mock, state };
}

describe("job toast watcher", () => {
  test("restores a running job after a refresh and announces its finish", async () => {
    const { state } = api({ running: [view("j1", "running")], queued: [], recent: [] });
    const first = renderApp("/");
    const title = await toasts().findByText("Fix Song 1");
    expect(title.closest(".alert")).not.toBeNull();
    first.unmount();
    renderApp("/");
    expect(await toasts().findByText("Fix Song 1")).toBeInTheDocument();
    state.jobs = { running: [], queued: [], recent: [view("j1", "done")] };
    expect(await toasts().findByText("Done", {}, { timeout: 5000 })).toBeInTheDocument();
  }, 15_000);

  test("more than four active jobs fold into one summary that opens the Jobs page on click", async () => {
    const more = Array.from({ length: 6 }, (_, i) => view(`q${i}`, "running", { map_id: `m${i}` }));
    api({ running: [view("r", "running", { map_id: "mr" }), ...more], queued: [], recent: [] });
    const { router } = renderApp("/");
    expect(await toasts().findByText("7 running")).toBeInTheDocument();
    expect(document.querySelectorAll(".toast-stack .alert")).toHaveLength(1);
    await userEvent.setup().click(toasts().getByText("7 running"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/jobs"));
  });

  test("a closed summary stays closed while folded and returns after the count drops and rises", async () => {
    const mk = (n: number) =>
      Array.from({ length: n }, (_, i) =>
        view(`q${i}`, "running", { map_id: `m${i}`, title: `Song ${i}` }),
      );
    const run = view("r", "running", { map_id: "mr", title: "Song r" });
    const { state, calls } = api({ running: [run, ...mk(5)], queued: [], recent: [] });
    const { router } = renderApp("/");
    expect(await toasts().findByText("6 running")).toBeInTheDocument();
    await userEvent.setup().click(toasts().getByText("6 running"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/jobs"));
    const polls = () => calls.filter((u) => u.pathname === "/api/jobs").length;
    const before = polls();
    state.jobs = { running: [run, ...mk(6)], queued: [], recent: [] };
    await waitFor(() => expect(polls()).toBeGreaterThan(before + 1), { timeout: 8000 });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 100));
    });
    expect(toasts().queryByText(/^\d+ running$/)).toBeNull();
    state.jobs = { running: mk(3), queued: [], recent: [] };
    await waitFor(() => expect(toasts().getAllByText(/^Fix Song \d$/)).toHaveLength(3), {
      timeout: 8000,
    });
    state.jobs = { running: [run, ...mk(5)], queued: [], recent: [] };
    expect(await toasts().findByText("6 running", {}, { timeout: 8000 })).toBeVisible();
  }, 40_000);

  test("a page-finished job is not adopted from a stale running list", async () => {
    const report = {
      map_id: "id0000000001",
      folder: "Folder 1 [saber-tooth]",
      fixed_id: "id0000000099",
      applied: 7,
      errors: 0,
      before: {},
      after: {},
      unfixed: [],
    };
    report.before = { Easy: { errors: { "missing-difficulty": 1 }, warnings: {} } };
    // An unrelated running job keeps the jobs list polling every 2 s.
    const other = view("jx", "running", { kind: "scan", map_id: "mx", progress: "busy" });
    const { state, calls } = api({ running: [other], queued: [], recent: [] }, (url) =>
      url.pathname === "/api/jobs/jf"
        ? { id: "jf", kind: "fix", error: null, status: "done", result: report }
        : undefined,
    );
    renderApp("/");
    const link = await screen.findByRole("link", { name: "Song 1" });
    await userEvent.setup().click(
      within(link.closest("[role=row]") as HTMLElement).getByRole("button", {
        name: "Fix Song 1",
      }),
    );
    // The cached list still shows the finished job as running.
    state.jobs = { running: [other, view("jf", "running")], queued: [], recent: [] };
    await toasts().findByText("Fixed: written to Folder 1 [saber-tooth]", {}, { timeout: 5000 });
    const polls = () => calls.filter((u) => u.pathname === "/api/jobs").length;
    const before = polls();
    await waitFor(() => expect(polls()).toBeGreaterThan(before), { timeout: 4000 });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 300));
    });
    expect(toasts().getByText("Fixed: written to Folder 1 [saber-tooth]")).toBeInTheDocument();
    expect(toasts().queryByText("Running")).toBeNull();
    state.jobs = { running: [other], queued: [], recent: [view("jf", "done")] };
    await act(async () => {
      await new Promise((r) => setTimeout(r, 2500));
    });
    expect(toasts().queryByText("Done")).toBeNull();
  }, 40_000);

  test("a stub that answers {} for everything raises no job toast", async () => {
    const { calls } = api({});
    renderApp("/");
    await waitFor(() => expect(calls.some((u) => u.pathname === "/api/jobs")).toBe(true));
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    expect(document.querySelector(".toast-stack")?.textContent).toBe("");
  });

  test("a job whose page unmounted keeps one toast and its finish shows", async () => {
    let phase: "running" | "done" = "running";
    const report = {
      map_id: "id0000000001",
      folder: "Folder 1 [saber-tooth]",
      fixed_id: "id0000000099",
      applied: 7,
      errors: 0,
      before: {},
      after: {},
      unfixed: [],
    };
    const { state } = api({ running: [], queued: [], recent: [] }, (url) =>
      url.pathname === "/api/jobs/jf"
        ? {
            id: "jf",
            kind: "fix",
            error: null,
            status: phase,
            result: phase === "done" ? report : null,
          }
        : undefined,
    );
    const { router } = renderApp("/");
    const user = userEvent.setup();
    const link = await screen.findByRole("link", { name: "Song 1" });
    await user.click(
      within(link.closest("[role=row]") as HTMLElement).getByRole("button", { name: "Fix Song 1" }),
    );
    await toasts().findByText("Fix Song 1");
    await act(async () => {
      await router.navigate("/about");
    });
    state.jobs = { running: [view("jf", "running")], queued: [], recent: [] };
    await new Promise((r) => setTimeout(r, 2200));
    expect(toasts().getAllByText(/^Fix Song 1$/)).toHaveLength(1);
    phase = "done";
    state.jobs = { running: [], queued: [], recent: [view("jf", "done")] };
    expect(
      await toasts().findByText(/Fixed: written to|^Done$/, {}, { timeout: 6000 }),
    ).toBeInTheDocument();
  }, 20_000);

  test("a map page job takes over when the page unmounts: one toast, then its Done", async () => {
    let phase: "running" | "done" = "running";
    const { state } = api({ running: [], queued: [], recent: [] }, (url) => {
      if (url.pathname === "/api/maps/id0000000001") return items[0];
      if (url.pathname === "/api/maps/id0000000001/proposals") return [];
      if (url.pathname === "/api/jobs/js") {
        return { id: "js", kind: "scan", error: null, status: phase, result: null };
      }
      return undefined;
    });
    const { router } = renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Scan" }));
    await toasts().findByText("Scan");
    let sawDanger = false;
    const watch = new MutationObserver(() => {
      if (document.querySelector(".toast-stack .alert-danger")) sawDanger = true;
    });
    watch.observe(document.body, { childList: true, subtree: true, attributes: true });
    await act(async () => {
      await router.navigate("/about");
    });
    state.jobs = { running: [view("js", "running", { kind: "scan" })], queued: [], recent: [] };
    await toasts().findByText("Scan Song 1", {}, { timeout: 13_000 });
    watch.disconnect();
    expect(sawDanger).toBe(false);
    expect(document.querySelectorAll(".toast-stack .alert")).toHaveLength(1);
    phase = "done";
    state.jobs = { running: [], queued: [], recent: [view("js", "done", { kind: "scan" })] };
    expect(await toasts().findByText("Done", {}, { timeout: 6000 })).toBeInTheDocument();
    expect(document.querySelectorAll(".toast-stack .alert")).toHaveLength(1);
    expect(document.querySelector(".toast-stack .alert-danger")).toBeNull();
  }, 40_000);
});
