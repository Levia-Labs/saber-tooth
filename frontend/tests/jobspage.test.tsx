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

describe("Jobs page", () => {
  test("lists running, queued and recent jobs and counts the active ones", async () => {
    serve(FULL);
    renderApp("/jobs");
    expect(await screen.findByRole("heading", { name: "Running" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Queued" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Recent" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Acid Rain" }).getAttribute("href")).toBe("/maps/m1");
    expect(screen.getByText("round 2 of 6")).toBeTruthy();
    expect(screen.getByText("boom")).toBeTruthy();
    const tabs = screen.getByRole("navigation", { name: "Section" });
    expect(within(tabs).getByText("3")).toBeTruthy();
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
    fireEvent.click(await screen.findByRole("button", { name: "Cancel Title q1" }));
    await waitFor(() => expect(deletes).toEqual(["/api/jobs/q1"]));
  });

  test("an empty list says so and the tab has no count", async () => {
    serve({ running: [], queued: [], recent: [] });
    renderApp("/jobs");
    expect(await screen.findByText("Nothing running or queued.")).toBeTruthy();
    const tabs = screen.getByRole("navigation", { name: "Section" });
    expect(within(tabs).queryByLabelText(/active/)).toBeNull();
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
