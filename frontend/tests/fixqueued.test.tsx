import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FACETS, item, mockFetch, renderApp, toasts } from "./helpers";

const items = [item(1, { status: "error", errors: 2 })];

describe("fix toast while queued", () => {
  test("none while the job waits; the running toast appears when it starts", async () => {
    const s = { status: "queued", polls: 0 };
    mockFetch((url, init) => {
      if (init?.method === "POST") return { job: "jq" };
      if (url.pathname === "/api/maps/facets") return FACETS;
      if (url.pathname === "/api/jobs/jq") {
        s.polls += 1;
        return { id: "jq", kind: "fix", status: s.status, position: 1, error: null, result: null };
      }
      if (url.pathname === "/api/jobs") return { running: [], queued: [], recent: [] };
      return { items, total: items.length, offset: 0, limit: 40 };
    });
    renderApp("/");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Fix Song 1" }));
    const stack = () => document.querySelector(".toast-stack")?.textContent ?? "";
    expect(stack()).toBe("");
    await waitFor(() => expect(s.polls).toBeGreaterThanOrEqual(2), { timeout: 6000 });
    expect(stack()).toBe("");
    s.status = "running";
    expect(await toasts().findByText("Running", {}, { timeout: 6000 })).toBeInTheDocument();
  }, 20_000);
});

describe("library rows and active jobs", () => {
  test("clicking Fix refetches the list so a now-queued map leaves a view that excludes it", async () => {
    const s = { fixed: false };
    const two = item(2, { status: "ok" });
    mockFetch((url, init) => {
      if (init?.method === "POST") {
        s.fixed = true;
        return { job: "jq" };
      }
      if (url.pathname === "/api/maps/facets") return FACETS;
      if (url.pathname === "/api/jobs/jq") return { id: "jq", kind: "fix", status: "queued" };
      if (url.pathname === "/api/jobs") return { running: [], queued: [], recent: [] };
      const list = s.fixed ? [two] : [...items, two];
      return { items: list, total: list.length, offset: 0, limit: 40 };
    });
    renderApp("/");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Fix Song 1" }));
    await waitFor(() => expect(screen.queryByRole("link", { name: "Song 1" })).toBeNull());
    expect(screen.getByRole("link", { name: "Song 2" })).toBeInTheDocument();
  });

  test("the status cell shows the queue position of a queued map and rounds of a running one", async () => {
    const queued = item(1, {
      status: "queued",
      job: { id: "a", kind: "fix", status: "queued", position: 2, progress: null },
    });
    const running = item(2, {
      status: "fixing",
      job: { id: "b", kind: "fix", status: "running", position: null, progress: "round 2 of 5" },
    });
    mockFetch((url) => {
      if (url.pathname === "/api/maps/facets") return FACETS;
      if (url.pathname.startsWith("/api/jobs")) return { running: [], queued: [], recent: [] };
      return { items: [queued, running], total: 2, offset: 0, limit: 40 };
    });
    renderApp("/");
    expect(await screen.findByRole("img", { name: "Queued, position 2" })).toHaveTextContent("#2");
    expect(screen.getByRole("img", { name: "Running, round 2 of 5" })).toHaveTextContent("2/5");
  });
});
