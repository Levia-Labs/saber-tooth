import { describe, expect, test } from "vitest";
import { planToasts, SUMMARY_KEY, toastKey } from "../src/lib/jobtoasts";
import type { JobLists, JobView } from "../src/api/types";

const v = (id: string, status: JobView["status"], extra: Partial<JobView> = {}): JobView => ({
  id,
  kind: "fix",
  status,
  map_id: `m-${id}`,
  title: `Song ${id}`,
  map_exists: true,
  created_at: "2026-10-29T10:00:00Z",
  started_at: null,
  updated_at: "2026-10-29T10:00:00Z",
  progress: null,
  progress_at: null,
  error: null,
  position: null,
  ...extra,
});
const lists = (p: Partial<JobLists>): JobLists => ({ running: [], queued: [], recent: [], ...p });
const none = new Set<string>();

describe("planToasts", () => {
  test("restores a keyed progress toast per unowned active job", () => {
    const plan = planToasts(
      new Map(),
      lists({
        running: [v("a", "running", { progress: "round 2 of 6" })],
        queued: [v("b", "queued", { position: 1 })],
      }),
      none,
    );
    expect(plan.show.map((t) => [t.key, t.title, t.message])).toEqual([
      ["Fix:m-a", "Fix Song a", "Round 2 of 6"],
      ["Fix:m-b", "Fix Song b", "Queued, position 1"],
    ]);
    expect(plan.summary).toBeNull();
  });

  test("does not re-announce an unchanged message", () => {
    const first = planToasts(new Map(), lists({ running: [v("a", "running")] }), none);
    const again = planToasts(first.next, lists({ running: [v("a", "running")] }), none);
    expect(again.show).toEqual([]);
  });

  test("leaves jobs a page is polling alone", () => {
    const plan = planToasts(new Map(), lists({ running: [v("a", "running")] }), new Set(["a"]));
    expect(plan.show).toEqual([]);
    expect(plan.next.size).toBe(0);
  });

  test("announces the finish of a tracked job", () => {
    const prev = new Map([
      ["a", { key: "Fix:m-a", message: "Running" }],
      ["b", { key: "Fix:m-b", message: "Running" }],
    ]);
    const plan = planToasts(
      prev,
      lists({
        recent: [v("a", "done"), v("b", "failed", { error: "boom" })],
      }),
      none,
    );
    expect(plan.show.map((t) => [t.key, t.variant, t.message])).toEqual([
      ["Fix:m-a", "success", "Done"],
      ["Fix:m-b", "danger", "boom"],
    ]);
    expect(plan.next.size).toBe(0);
  });

  test("a tracked job missing from every list has its toast withdrawn", () => {
    const prev = new Map([["a", { key: "Fix:m-a", message: "Running" }]]);
    const plan = planToasts(prev, lists({}), none);
    expect(plan.withdraw).toEqual(["Fix:m-a"]);
  });

  test("more than four unowned active jobs fold into one summary", () => {
    const queued = Array.from({ length: 98 }, (_, i) => v(`q${i}`, "queued", { position: i + 1 }));
    const plan = planToasts(new Map(), lists({ running: [v("r", "running")], queued }), none);
    expect(plan.summary).toEqual({ running: 1, waiting: 98 });
    expect(plan.show.every((t) => t.key === SUMMARY_KEY)).toBe(true);
  });

  test("in summary mode successes are silent and failures still show one each", () => {
    const active = Array.from({ length: 6 }, (_, i) => v(`q${i}`, "queued", { position: i + 1 }));
    const prev = new Map([
      ["a", { key: "Fix:m-a", message: "Running" }],
      ["b", { key: "Fix:m-b", message: "Running" }],
    ]);
    const plan = planToasts(
      prev,
      lists({
        queued: active,
        recent: [v("a", "done"), v("b", "failed", { error: "boom" })],
      }),
      none,
    );
    const finished = plan.show.filter((t) => t.key !== SUMMARY_KEY);
    expect(finished.map((t) => [t.key, t.variant])).toEqual([["Fix:m-b", "danger"]]);
  });

  test("per-job toasts come back when the summary unfolds with unchanged messages", () => {
    const six = Array.from({ length: 6 }, (_, i) => v(`q${i}`, "queued", { position: i + 1 }));
    const folded = planToasts(new Map(), lists({ queued: six }), none);
    expect(folded.summary).not.toBeNull();
    const back = planToasts(folded.next, lists({ queued: six.slice(0, 3) }), none);
    expect(back.summary).toBeNull();
    expect(back.show.map((t) => [t.key, t.variant])).toEqual([
      ["Fix:m-q0", "progress"],
      ["Fix:m-q1", "progress"],
      ["Fix:m-q2", "progress"],
    ]);
  });

  test("keys match the page keys", () => {
    expect(toastKey(v("a", "running"))).toBe("Fix:m-a");
    expect(toastKey(v("g", "queued", { kind: "generate", map_id: null }))).toBe("generate-job-g");
    expect(toastKey(v("l", "queued", { kind: "learn", map_id: null }))).toBe("Learn lightshows");
  });
});
