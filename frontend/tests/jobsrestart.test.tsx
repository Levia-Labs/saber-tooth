import { fireEvent, waitFor, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { JobView } from "../src/api/types";
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

const rowOf = (id: string) => document.querySelector(`[data-job="${id}"]`) as HTMLElement;
const loaded = () => waitFor(() => expect(document.querySelector("[data-job]")).not.toBeNull());

describe("Jobs page restart", () => {
  test("a cancelled row offers Restart, posting to the retry endpoint; done rows offer nothing", async () => {
    const posts: string[] = [];
    mockFetch(async (url, init) => {
      if (init?.method === "POST") {
        posts.push(url.pathname);
        return job("n1", { status: "queued" });
      }
      return url.pathname === "/api/jobs"
        ? {
            running: [],
            queued: [],
            recent: [job("a", { status: "done" }), job("c", { status: "cancelled", map_id: "m9" })],
          }
        : {};
    });
    renderApp("/jobs");
    await loaded();
    expect(within(rowOf("a")).queryByRole("button", { name: "Restart job" })).toBeNull();
    const restart = within(rowOf("c")).getByRole("button", { name: "Restart job" });
    expect(restart.querySelector("svg")).not.toBeNull();
    fireEvent.click(restart);
    await waitFor(() => expect(posts).toEqual(["/api/jobs/c/retry"]));
  });
});
