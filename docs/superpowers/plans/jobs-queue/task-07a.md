### Task 7: Toasts that survive refresh and navigation

**Files:**

- Create: `frontend/src/lib/jobtoasts.ts`, `frontend/src/components/JobToasts.tsx`
- Modify: `frontend/src/App.tsx` (`Shell`, render `<JobToasts />` once inside the providers)
- Modify: `frontend/src/components/README.md`, `frontend/src/lib/README.md`
- Test: `frontend/tests/jobtoasts.test.ts`, `frontend/tests/jobtoastsApp.test.tsx` (new)

**Interfaces:**

- Consumes: `useJobLists`, `watchedJobs` (Task 5); `useAnnounce`, `useWithdraw` (`components/Announcer`); `AnnounceInput` (`lib/announcements`); `fixKey` (`lib/fixToast`).
- Produces:
  - `SUMMARY_KEY = "jobs-summary"`, `SUMMARY_ABOVE = 4`
  - `toastKey(job: JobView): string`: fix `Fix:<map_id>`, scan `Scan:<map_id>`, apply `Apply:<map_id>`, crop `Crop:<map_id>`, learn `Learn lightshows`, bs-download `Download maps`, generate `generate-job-<id>`; these match the keys the pages use, so a page's toast and the watcher's toast replace each other.
  - `type Tracked = Map<string, { key: string; message: string }>`
  - `planToasts(prev: ReadonlyMap<string, { key: string; message: string }>, lists: JobLists, owned: ReadonlySet<string>): { show: AnnounceInput[]; withdraw: string[]; next: Tracked; summary: { running: number; waiting: number } | null }`. `prev`/`next` map each tracked (unowned, active) job id to its toast key and the message last shown; keeping the key means a job that vanished from every list can still have its toast withdrawn.

Ruling recorded for the spec's point 7.2: the summary replaces the watcher's own per-job progress toasts. Toasts of jobs started in this page session belong to their page (`pollJob` owns them through `watchedJobs`) and behave as today; after a refresh every job is unowned, so the summary covers them all.

- [ ] **Step 1: Write the failing tests**

`frontend/tests/jobtoasts.test.ts`:

```ts
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

  test("keys match the page keys", () => {
    expect(toastKey(v("a", "running"))).toBe("Fix:m-a");
    expect(toastKey(v("g", "queued", { kind: "generate", map_id: null }))).toBe("generate-job-g");
    expect(toastKey(v("l", "queued", { kind: "learn", map_id: null }))).toBe("Learn lightshows");
  });
});
```

`frontend/tests/jobtoastsApp.test.tsx`, with `mockFetch` and `renderApp` from `./helpers` and the `toasts()` helper:

1. `/api/jobs` answers one running fix; rendering `/` shows a progress toast titled "Fix Song a" inside the toast stack. Unmount, render again (a refresh): the toast is back. When the next answer moves the job to `recent` as `done`, a success toast "Done" replaces it.
2. `/api/jobs` answers 1 running and 6 queued: the toast stack holds one progress toast titled "1 running, 6 waiting" with a "Show jobs" button; pressing it navigates to `/jobs`.
3. Existing stubs that answer `/api/jobs` with `{}`: no job toast appears (render `/` with a handler that returns `{}` for everything and assert `toasts()` is empty after the first poll).
4. Navigation hand-off: start a Fix from the library row (as the existing fix-button test does), navigate to `/about` so the row unmounts, and have `/api/jobs` report the job running: exactly one toast with key-equivalent title "Fix ..." exists (no duplicate), and its finish shows.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `task st:web:test -- jobtoasts`
Expected: FAIL (modules missing).

Continued in [task-07b.md](task-07b.md).
