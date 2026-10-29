import { describe, expect, test, vi } from "vitest";
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
  cancel_requested: false,
  ...extra,
});
const lists = (p: Partial<JobLists>): JobLists => ({ running: [], queued: [], recent: [], ...p });
const none = new Set<string>();

describe("planToasts", () => {
  test("a toast per unowned running job and none for queued jobs", () => {
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
    ]);
    expect(plan.next.has("b")).toBe(false);
    expect(plan.summary).toBeNull();
  });

  test("queued jobs never count towards the summary", () => {
    const queued = Array.from({ length: 20 }, (_, i) => v(`q${i}`, "queued", { position: i }));
    const plan = planToasts(new Map(), lists({ running: [v("r", "running")], queued }), none);
    expect(plan.summary).toBeNull();
    expect(plan.show).toHaveLength(1);
  });

  test("a running toast has no buttons, carries rounds when known and opens through open", () => {
    const open = vi.fn();
    const plan = planToasts(
      new Map(),
      lists({
        running: [v("a", "running", { progress: "round 2 of 6" }), v("b", "running")],
      }),
      none,
      open,
    );
    const [a, b] = plan.show;
    expect(a?.actions).toBeUndefined();
    expect(a?.rounds).toBe("2/6");
    expect(b?.rounds).toBeUndefined();
    a?.onOpen?.();
    expect(open).toHaveBeenCalledTimes(1);
  });

  test("outcome toasts open the Jobs page too", () => {
    const open = vi.fn();
    const first = planToasts(new Map(), lists({ running: [v("a", "running")] }), none, open);
    const plan = planToasts(
      first.next,
      lists({ recent: [v("a", "failed", { error: "x" })] }),
      none,
      open,
    );
    plan.show[0]?.onOpen?.();
    expect(open).toHaveBeenCalledTimes(1);
  });

  test("a dismissed progress toast stays closed across message changes; the outcome still shows", () => {
    const dismissed = new Set<string>();
    const first = planToasts(
      new Map(),
      lists({ running: [v("a", "running")] }),
      none,
      undefined,
      dismissed,
    );
    first.show[0]?.onDismiss?.();
    expect(dismissed.has("a")).toBe(true);
    const asked = planToasts(
      first.next,
      lists({ running: [v("a", "running", { cancel_requested: true })] }),
      none,
      undefined,
      dismissed,
    );
    expect(asked.show).toEqual([]);
    expect(asked.next.has("a")).toBe(true);
    const done = planToasts(
      asked.next,
      lists({ recent: [v("a", "cancelled")] }),
      none,
      undefined,
      dismissed,
    );
    expect(done.show.map((t) => [t.variant, t.message])).toEqual([["info", "Cancelled"]]);
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

  test("announces the outcome of a tracked job; a cancelled one reads Cancelled", () => {
    const prev = new Map([
      ["a", { key: "Fix:m-a", message: "Running" }],
      ["b", { key: "Fix:m-b", message: "Running" }],
      ["c", { key: "Fix:m-c", message: "Running" }],
    ]);
    const plan = planToasts(
      prev,
      lists({
        recent: [
          v("a", "done"),
          v("b", "failed", { error: "boom" }),
          v("c", "cancelled", { error: "interrupted" }),
        ],
      }),
      none,
    );
    expect(plan.show.map((t) => [t.key, t.variant, t.message])).toEqual([
      ["Fix:m-a", "success", "Done"],
      ["Fix:m-b", "danger", "boom"],
      ["Fix:m-c", "info", "Cancelled"],
    ]);
    expect(plan.next.size).toBe(0);
  });

  test("a tracked job missing from every list has its toast withdrawn", () => {
    const prev = new Map([["a", { key: "Fix:m-a", message: "Running" }]]);
    const plan = planToasts(prev, lists({}), none);
    expect(plan.withdraw).toEqual(["Fix:m-a"]);
  });

  test("more than four unowned running jobs fold into one summary", () => {
    const running = Array.from({ length: 5 }, (_, i) => v(`r${i}`, "running"));
    const plan = planToasts(new Map(), lists({ running }), none);
    expect(plan.summary).toEqual({ running: 5 });
    expect(plan.show.every((t) => t.key === SUMMARY_KEY)).toBe(true);
  });

  test("in summary mode successes are silent and failures still show one each", () => {
    const active = Array.from({ length: 6 }, (_, i) => v(`r${i}`, "running"));
    const prev = new Map([
      ["a", { key: "Fix:m-a", message: "Running" }],
      ["b", { key: "Fix:m-b", message: "Running" }],
    ]);
    const plan = planToasts(
      prev,
      lists({ running: active, recent: [v("a", "done"), v("b", "failed", { error: "boom" })] }),
      none,
    );
    const finished = plan.show.filter((t) => t.key !== SUMMARY_KEY);
    expect(finished.map((t) => [t.key, t.variant])).toEqual([["Fix:m-b", "danger"]]);
  });

  test("per-job toasts come back when the summary unfolds with unchanged messages", () => {
    const six = Array.from({ length: 6 }, (_, i) => v(`r${i}`, "running"));
    const folded = planToasts(new Map(), lists({ running: six }), none);
    expect(folded.summary).not.toBeNull();
    const back = planToasts(folded.next, lists({ running: six.slice(0, 3) }), none);
    expect(back.summary).toBeNull();
    expect(back.show.map((t) => [t.key, t.variant])).toEqual([
      ["Fix:m-r0", "progress"],
      ["Fix:m-r1", "progress"],
      ["Fix:m-r2", "progress"],
    ]);
  });

  test("keys match the page keys", () => {
    expect(toastKey(v("a", "running"))).toBe("Fix:m-a");
    expect(toastKey(v("g", "queued", { kind: "generate", map_id: null }))).toBe("generate-job-g");
    expect(toastKey(v("l", "queued", { kind: "learn", map_id: null }))).toBe("Learn lightshows");
  });
});
