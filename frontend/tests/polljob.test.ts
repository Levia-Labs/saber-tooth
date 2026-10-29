import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { JobFailed, ownedJobs, pollJob, watchedJobs } from "../src/api/jobs";
import { mockFetch } from "./helpers";

const MIN = 60_000;
let state: { status: string; position?: number | null };

beforeEach(() => {
  vi.useFakeTimers();
  state = { status: "queued", position: 3 };
  mockFetch(() => ({ id: "j1", kind: "fix", error: null, result: null, ...state }));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("pollJob", () => {
  test("never times out while queued and reports the queue position", async () => {
    const statuses: string[] = [];
    const p = pollJob("j1", new AbortController().signal, (s) => statuses.push(s));
    await vi.advanceTimersByTimeAsync(40 * MIN);
    expect(statuses).toContain("queued, position 3");
    state = { status: "running" };
    await vi.advanceTimersByTimeAsync(10_000);
    state = { status: "done" };
    await vi.advanceTimersByTimeAsync(10_000);
    await expect(p).resolves.toMatchObject({ status: "done" });
  });

  test("times out after 31 minutes of running", async () => {
    state = { status: "running" };
    const p = pollJob("j1", new AbortController().signal, () => {});
    const settled = expect(p).rejects.toThrow("timed out after 30 minutes");
    await vi.advanceTimersByTimeAsync(31 * MIN);
    await settled;
  });

  test("a cancelled job rejects with JobFailed cancelled", async () => {
    state = { status: "cancelled" };
    const p = pollJob("j1", new AbortController().signal, () => {});
    const settled = expect(p).rejects.toSatisfy(
      (e) => e instanceof JobFailed && e.message === "cancelled",
    );
    await vi.advanceTimersByTimeAsync(1000);
    await settled;
  });

  test("watchedJobs holds the id while polling only", async () => {
    const p = pollJob("j1", new AbortController().signal, () => {});
    await vi.advanceTimersByTimeAsync(10);
    expect(watchedJobs.has("j1")).toBe(true);
    state = { status: "done" };
    await vi.advanceTimersByTimeAsync(5000);
    await p;
    expect(watchedJobs.has("j1")).toBe(false);
  });

  test("ownedJobs keeps a job whose poll settled from the server, not one that was aborted", async () => {
    state = { status: "done" };
    const p = pollJob("j7", new AbortController().signal, () => {});
    await vi.advanceTimersByTimeAsync(10);
    await p;
    expect(watchedJobs.has("j7")).toBe(false);
    expect(ownedJobs.has("j7")).toBe(true);
    state = { status: "failed" };
    const bad = expect(pollJob("j8", new AbortController().signal, () => {})).rejects.toThrow();
    await vi.advanceTimersByTimeAsync(10);
    await bad;
    expect(ownedJobs.has("j8")).toBe(true);
    state = { status: "running" };
    const ctl = new AbortController();
    const gone = expect(pollJob("j9", ctl.signal, () => {})).rejects.toThrow("cancelled");
    await vi.advanceTimersByTimeAsync(10);
    ctl.abort();
    await vi.advanceTimersByTimeAsync(10);
    await gone;
    expect(ownedJobs.has("j9")).toBe(false);
  });

  test("two polls on one id: aborting the first keeps the id watched", async () => {
    const first = new AbortController();
    const p1 = pollJob("j1", first.signal, () => {});
    const p2 = pollJob("j1", new AbortController().signal, () => {});
    const s1 = expect(p1).rejects.toThrow("cancelled");
    await vi.advanceTimersByTimeAsync(10);
    first.abort();
    await vi.advanceTimersByTimeAsync(10);
    await s1;
    expect(watchedJobs.has("j1")).toBe(true);
    state = { status: "done" };
    await vi.advanceTimersByTimeAsync(5000);
    await p2;
    expect(watchedJobs.has("j1")).toBe(false);
  });
});
