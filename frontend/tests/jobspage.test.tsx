import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { JobLists, JobView } from "../src/api/types";
import { mockFetch, renderApp } from "./helpers";

const NOW = new Date().toISOString();

function job(id: string, patch: Partial<JobView> = {}): JobView {
  return {
    id,
    kind: "fix",
    status: "queued",
    map_id: null,
    title: `Title ${id}`,
    map_exists: false,
    created_at: NOW,
    started_at: null,
    updated_at: NOW,
    progress: null,
    progress_at: null,
    error: null,
    position: null,
    cancel_requested: false,
    ...patch,
  };
}

function serve(lists: JobLists) {
  return mockFetch((url) => (url.pathname === "/api/jobs" ? lists : {}));
}

const FULL: JobLists = {
  running: [
    job("r1", {
      status: "running",
      title: "Acid Rain",
      map_id: "m1",
      map_exists: true,
      started_at: NOW,
      progress: "round 2 of 6",
    }),
  ],
  queued: [job("q1", { position: 1 }), job("q2", { position: 2, kind: "scan" })],
  recent: [job("d1", { status: "failed", error: "boom", started_at: NOW })],
};

const rowOf = (id: string) => document.querySelector(`[data-job="${id}"]`) as HTMLElement;
const loaded = () => waitFor(() => expect(document.querySelector("[data-job]")).not.toBeNull());
const order = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((r) => r.getAttribute("data-job"));

describe("Jobs page", () => {
  test("one table lists running, queued and finished jobs in the default order", async () => {
    serve(FULL);
    renderApp("/jobs");
    await loaded();
    expect(screen.getByRole("table", { name: "Jobs" })).toBeTruthy();
    expect(order()).toEqual(["r1", "q1", "q2", "d1"]);
    expect(screen.queryByRole("heading", { name: "Running" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Queued" })).toBeNull();
    expect(screen.getByRole("link", { name: "Acid Rain" }).getAttribute("href")).toBe("/maps/m1");
    expect(within(rowOf("r1")).getByText("2/6")).toBeTruthy();
    expect(screen.getByText("boom")).toBeTruthy();
    const tabs = screen.getByRole("navigation", { name: "Section" });
    expect(within(tabs).getByText("3")).toBeTruthy();
  });

  test("columns mirror the library: Icon, Title, Length, Operation, Status, Queue #, Rounds, Actions", async () => {
    serve(FULL);
    renderApp("/jobs");
    await loaded();
    const heads = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(heads).toEqual([
      "Icon",
      "Title",
      "Length",
      "Operation",
      "Status",
      "Queue #",
      "Rounds",
      "Actions",
    ]);
    const cells = within(rowOf("r1")).getAllByRole("cell");
    expect(cells).toHaveLength(8);
    expect(cells[3]?.textContent).toBe("Fix");
    expect(cells[6]?.textContent).toBe("2/6");
  });

  test("status cells are library chips with a tooltip name; queue # only when queued", async () => {
    serve(FULL);
    renderApp("/jobs");
    await loaded();
    const chip = (id: string) => rowOf(id).querySelector(".chip") as HTMLElement;
    expect(chip("r1").className).toContain("chip-fixing");
    expect(chip("r1").getAttribute("aria-label")).toBe("Running");
    expect(chip("q2").className).toContain("chip-queued");
    expect(chip("q2").getAttribute("aria-label")).toBe("Queued");
    expect(chip("d1").className).toContain("chip-error");
    expect(chip("d1").getAttribute("aria-label")).toBe("Failed");
    expect(within(rowOf("q2")).getAllByRole("cell")[5]?.textContent).toBe("2");
    expect(within(rowOf("r1")).getAllByRole("cell")[5]?.textContent).toBe("");
    expect(within(rowOf("q2")).getAllByRole("cell")[3]?.textContent).toBe("Scan");
    expect(within(rowOf("q1")).getAllByRole("cell")[6]?.textContent).toBe("");
  });

  test("a queued row has no waiting counter and no length", async () => {
    serve(FULL);
    renderApp("/jobs");
    await loaded();
    expect(screen.queryByText(/waiting/)).toBeNull();
    expect(rowOf("q1").querySelector(".jc-length")?.textContent).toBe("");
  });

  test("the icon cell shows the map cover when the map exists, else the kind icon", async () => {
    serve(FULL);
    renderApp("/jobs");
    await loaded();
    expect(rowOf("r1").querySelector("img.cover")?.getAttribute("src")).toBe("/api/maps/m1/cover");
    expect(rowOf("q1").querySelector(".jc-cover svg")).not.toBeNull();
    expect(rowOf("q1").querySelector("img")).toBeNull();
  });

  test("Cancel on a queued job sends DELETE for that job", async () => {
    const deletes: string[] = [];
    mockFetch((url, init) => {
      if (init?.method === "DELETE") {
        deletes.push(url.pathname);
        return { id: "q1", kind: "fix", status: "cancelled" };
      }
      return url.pathname === "/api/jobs" ? FULL : {};
    });
    renderApp("/jobs");
    const buttons = await screen.findAllByRole("button", { name: "Cancel job" });
    fireEvent.click(within(rowOf("q1")).getByRole("button", { name: "Cancel job" }));
    expect(buttons.length).toBeGreaterThan(0);
    await waitFor(() => expect(deletes).toEqual(["/api/jobs/q1"]));
  });

  test("a running job has Cancel; once requested it reads Cancelling and is disabled", async () => {
    serve({
      running: [
        job("a", { status: "running", started_at: NOW }),
        job("b", { status: "running", started_at: NOW, cancel_requested: true }),
      ],
      queued: [],
      recent: [],
    });
    renderApp("/jobs");
    await loaded();
    const cancel = within(rowOf("a")).getByRole("button", { name: "Cancel job" });
    expect((cancel as HTMLButtonElement).disabled).toBe(false);
    expect(cancel.querySelector("svg")).not.toBeNull();
    const busy = within(rowOf("b")).getByRole("button", { name: "Cancelling job" });
    expect((busy as HTMLButtonElement).disabled).toBe(true);
    expect(within(rowOf("b")).getByRole("img", { name: "Cancelling" })).toBeTruthy();
  });

  test("finished rows name their status in words and have no Cancel", async () => {
    serve({
      running: [],
      queued: [],
      recent: [
        job("a", { status: "done" }),
        job("b", { status: "failed", error: "boom" }),
        job("c", { status: "cancelled" }),
      ],
    });
    renderApp("/jobs");
    await loaded();
    expect(within(rowOf("a")).getByRole("img", { name: "Done" })).toBeTruthy();
    expect(within(rowOf("b")).getByRole("img", { name: "Failed" })).toBeTruthy();
    expect(within(rowOf("c")).getByRole("img", { name: "Cancelled" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /^Cancel/i })).toBeNull();
  });

  test("a running job without progress renders no empty progress cell", async () => {
    serve({ running: [job("r", { status: "running", started_at: NOW })], queued: [], recent: [] });
    const { container } = renderApp("/jobs");
    await loaded();
    expect(container.querySelectorAll(".jobs-detail")).toHaveLength(0);
  });

  test("the Title filter narrows the rows and lives in the URL", async () => {
    serve(FULL);
    const { router } = renderApp("/jobs?q=acid");
    await loaded();
    expect(order()).toEqual(["r1"]);
    expect(router.state.location.search).toBe("?q=acid");
  });

  test("status and kind filters come from the URL", async () => {
    serve(FULL);
    renderApp("/jobs?status=queued&kind=scan");
    await loaded();
    expect(order()).toEqual(["q2"]);
  });

  test("the Title sort toggle reorders and flips", async () => {
    serve(FULL);
    const { router } = renderApp("/jobs");
    await loaded();
    fireEvent.click(screen.getByRole("button", { name: "Sort by Title" }));
    expect(order()).toEqual(["r1", "d1", "q1", "q2"]);
    expect(router.state.location.search).toBe("?sort=title");
    fireEvent.click(screen.getByRole("button", { name: "Sort by Title" }));
    expect(order()).toEqual(["q2", "q1", "d1", "r1"]);
  });

  test("an empty list says so and the tab has no count", async () => {
    serve({ running: [], queued: [], recent: [] });
    renderApp("/jobs");
    expect(await screen.findByText("Nothing running or queued.")).toBeTruthy();
    const tabs = screen.getByRole("navigation", { name: "Section" });
    expect(within(tabs).queryByLabelText(/active/)).toBeNull();
  });

  test("filters that hide every job offer a way back", async () => {
    serve(FULL);
    renderApp("/jobs?q=zzz");
    expect(await screen.findByText(/No jobs match/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    await waitFor(() => expect(order()).toHaveLength(4));
  });

  test("all three tabs show and Jobs is the current one", async () => {
    serve({ running: [], queued: [], recent: [] });
    renderApp("/jobs");
    const tabs = await screen.findByRole("navigation", { name: "Section" });
    expect(within(tabs).getByRole("link", { name: "Library" })).toBeTruthy();
    expect(within(tabs).getByRole("link", { name: "BeatSaver" })).toBeTruthy();
    expect(within(tabs).getByRole("link", { name: "Jobs" }).getAttribute("aria-current")).toBe(
      "page",
    );
  });
});
