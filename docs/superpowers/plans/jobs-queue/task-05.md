### Task 5: Frontend job data layer

**Files:**

- Modify: `frontend/src/api/types.ts` (`JobState` line 19, `JobKind` line 20, `Job` lines 150-156)
- Modify: `frontend/src/api/client.ts` (beside `getJob`, line 100)
- Modify: `frontend/src/api/jobs.ts` (`pollJob`, lines 32-58)
- Modify: `frontend/src/api/queries.ts` (`keys`, line 26)
- Create: `frontend/src/api/joblist.ts`
- Modify: `frontend/src/api/README.md`
- Test: `frontend/tests/joblist.test.tsx` (new), `frontend/tests/polljob.test.ts` (new, or extend the existing pollJob test file if one exists: search `pollJob` under `frontend/tests`)

**Interfaces:**

- Produces:
  - `JobState = "queued" | "running" | "done" | "failed" | "cancelled"`; `JobKind` adds `"bs-download"`.
  - `interface JobView { id; kind: JobKind; status: JobState; map_id: string | null; title: string; map_exists: boolean; created_at: string; started_at: string | null; updated_at: string; progress: string | null; progress_at: string | null; error: string | null; position: number | null }`
  - `type Job = Pick<JobView, "id" | "kind" | "status" | "error"> & Partial<Omit<JobView, "id" | "kind" | "status" | "error">> & { result: Record<string, unknown> | null }` (the new fields are optional on `Job`, so existing test fixtures that build a four-field job still type-check).
  - `interface JobLists { running: JobView[]; queued: JobView[]; recent: JobView[] }`
  - `listJobs(signal?: AbortSignal): Promise<JobLists>`, `cancelJob(id: string): Promise<Job>`
  - `keys.jobs = ["jobs"] as const`
  - `normalizeJobLists(body: unknown): JobLists`, `activeCount(lists: JobLists): number`, `useJobLists(): JobLists` (React Query, polling per Global Constraint 4)
  - `watchedJobs: ReadonlySet<string>` exported from `jobs.ts`: ids a live `pollJob` is polling

- [ ] **Step 1: Write the failing tests**

`frontend/tests/joblist.test.tsx`:

```tsx
import { describe, expect, test } from "vitest";
import { activeCount, normalizeJobLists } from "../src/api/joblist";

const job = (id: string, status: string) => ({
  id,
  kind: "fix",
  status,
  map_id: null,
  title: "T",
  map_exists: false,
  created_at: "2026-10-29T10:00:00+00:00",
  started_at: null,
  updated_at: "2026-10-29T10:00:00+00:00",
  progress: null,
  progress_at: null,
  error: null,
  position: null,
});

describe("normalizeJobLists", () => {
  test("an empty or foreign body is an empty list, never a throw", () => {
    for (const body of [{}, null, "x", [], { running: "nope" }, { queued: [1, null] }]) {
      expect(normalizeJobLists(body)).toEqual({ running: [], queued: [], recent: [] });
    }
  });

  test("keeps well-formed rows", () => {
    const lists = normalizeJobLists({
      running: [job("a", "running")],
      queued: [job("b", "queued")],
      recent: [],
    });
    expect(lists.running.map((j) => j.id)).toEqual(["a"]);
    expect(activeCount(lists)).toBe(2);
  });
});
```

`frontend/tests/polljob.test.ts`: with `mockFetch` from `./helpers` and fake timers:

1. A job that stays `queued` for 40 simulated minutes, then `running`, then `done` resolves (no timeout while queued), and `onStatus` received `"queued, position 3"` while queued with `position: 3`.
2. A job that stays `running` for 31 simulated minutes rejects with the existing timeout error.
3. A `cancelled` job rejects with `JobFailed` whose message is `"cancelled"`.
4. `watchedJobs.has(id)` is true while polling and false after it settles.

Write these with `vi.useFakeTimers()` and `await vi.advanceTimersByTimeAsync(...)`; the mock returns the status from a variable the test changes.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `task st:web:test -- joblist polljob`
Expected: FAIL (module `../src/api/joblist` not found).

- [ ] **Step 3: Implement**

`frontend/src/api/client.ts`, after `getJob`:

```ts
export const listJobs = (signal?: AbortSignal): Promise<unknown> =>
  request("GET", "/api/jobs", undefined, signal);
export const cancelJob = (id: string): Promise<Job> => request("DELETE", `/api/jobs/${seg(id)}`);
```

`frontend/src/api/queries.ts`: add `jobs: ["jobs"] as const,` to `keys`.

`frontend/src/api/joblist.ts`:

```ts
// The job list behind the Jobs tab, its count and the toast watcher; one shared query.
import { useQuery } from "@tanstack/react-query";
import { listJobs } from "./client";
import { keys } from "./queries";
import type { JobLists, JobView } from "./types";

export const ACTIVE_POLL_MS = 2000;
export const IDLE_POLL_MS = 10_000;
const EMPTY: JobLists = { running: [], queued: [], recent: [] };

const isView = (v: unknown): v is JobView =>
  typeof v === "object" &&
  v !== null &&
  typeof (v as JobView).id === "string" &&
  typeof (v as JobView).status === "string";

const rows = (v: unknown): JobView[] => (Array.isArray(v) ? v.filter(isView) : []);

/** Any body becomes a list; test stubs answer unknown paths with `{}`. */
export function normalizeJobLists(body: unknown): JobLists {
  if (typeof body !== "object" || body === null || Array.isArray(body)) return EMPTY;
  const b = body as Record<string, unknown>;
  return { running: rows(b.running), queued: rows(b.queued), recent: rows(b.recent) };
}

export const activeCount = (lists: JobLists): number => lists.running.length + lists.queued.length;

export function useJobLists(): JobLists {
  const { data } = useQuery({
    queryKey: keys.jobs,
    queryFn: async ({ signal }) => normalizeJobLists(await listJobs(signal)),
    refetchInterval: (query) =>
      activeCount(query.state.data ?? EMPTY) > 0 ? ACTIVE_POLL_MS : IDLE_POLL_MS,
    refetchIntervalInBackground: false,
    retry: false,
  });
  return data ?? EMPTY;
}
```

`frontend/src/api/jobs.ts`, `pollJob`:

```ts
const watched = new Set<string>();
/** Ids a live pollJob is polling; the toast watcher leaves these to their page. */
export const watchedJobs: ReadonlySet<string> = watched;

export async function pollJob(
  jobId: string,
  signal: AbortSignal,
  onStatus: (status: string) => void,
): Promise<Job> {
  watched.add(jobId);
  try {
    let deadline = Number.POSITIVE_INFINITY; // the 30 minutes start once the job runs
    let delay = FIRST_DELAY_MS;
    let fails = 0;
    while (Date.now() < deadline && !signal.aborted) {
      try {
        const job = await getJob(jobId);
        fails = 0;
        if (job.status === "done") return job;
        if (job.status === "failed") throw new JobFailed(job.error ?? "job failed", job);
        if (job.status === "cancelled") throw new JobFailed("cancelled", job);
        if (job.status !== "queued" && deadline === Number.POSITIVE_INFINITY) {
          deadline = Date.now() + MAX_JOB_MS;
        }
        onStatus(
          job.status === "queued" && job.position ? `queued, position ${job.position}` : job.status,
        );
      } catch (err) {
        // keep the existing retry branch unchanged
      }
      // keep the existing sleep and backoff unchanged
    }
    // keep the existing timeout / abort ending unchanged
  } finally {
    watched.delete(jobId);
  }
}
```

The three "keep" comments mark the parts of the current function (lines 47-58) that stay as they are; move them inside the new `try` without changing them.

`types.ts`: apply the Interfaces block above.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `task st:web:test` then `task st:web:check`
Expected: PASS; the whole Vitest suite stays green.

- [ ] **Step 5: README and commit**

`frontend/src/api/README.md`: add `joblist.ts` ("the shared job list query, polling 2 s while jobs are active and 10 s when idle") and note `watchedJobs` on the `jobs.ts` row. Main thread commits: `task st:commit -- -m "feat(web): job list query, cancel call, and pollJob that waits in the queue without timing out" <files>`

---
