### Task 6: Jobs tab and page

**Files:**

- Modify: `frontend/src/components/SectionTabs.tsx`
- Create: `frontend/src/pages/JobsPage.tsx`, `frontend/src/lib/jobtime.ts`, `frontend/src/styles/jobs.css`
- Modify: `frontend/src/App.tsx` (lazy route beside `/beatsaver`, line 123)
- Modify: `frontend/src/components/README.md`, `frontend/src/pages/README.md`, `frontend/src/styles/README.md`, `frontend/src/lib/README.md` (whichever exist)
- Test: `frontend/tests/jobspage.test.tsx`, `frontend/tests/jobtime.test.ts` (new)

**Interfaces:**

- Consumes: `useJobLists`, `activeCount`, `cancelJob`, `keys.jobs` (Task 5).
- Produces:
  - `SectionTabs` `active: "library" | "beatsaver" | "jobs"`; a third item `{ key: "jobs", to: "/jobs", label: "Jobs", tip: "What the server is working on." }` with a count badge when `activeCount > 0`.
  - `jobtime.ts`: `STALE_MS = 10 * 60 * 1000`, `duration(fromIso: string, toMs: number): string` ("45 s", "3 min 12 s", "1 h 4 min"), `staleMinutes(job: JobView, nowMs: number): number | null`.
  - `JobsPage` at `/jobs`.

- [ ] **Step 1: Write the failing tests**

`frontend/tests/jobtime.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { duration, staleMinutes } from "../src/lib/jobtime";

const at = (iso: string) => Date.parse(iso);

describe("duration", () => {
  test("seconds, minutes and hours", () => {
    expect(duration("2026-10-29T10:00:00Z", at("2026-10-29T10:00:45Z"))).toBe("45 s");
    expect(duration("2026-10-29T10:00:00Z", at("2026-10-29T10:03:12Z"))).toBe("3 min 12 s");
    expect(duration("2026-10-29T10:00:00Z", at("2026-10-29T11:04:30Z"))).toBe("1 h 4 min");
  });
  test("bad or future input never shows a negative time", () => {
    expect(duration("nope", at("2026-10-29T10:00:00Z"))).toBe("0 s");
    expect(duration("2026-10-29T10:05:00Z", at("2026-10-29T10:00:00Z"))).toBe("0 s");
  });
});

describe("staleMinutes", () => {
  const base = {
    id: "a",
    kind: "fix" as const,
    status: "running" as const,
    map_id: null,
    title: "T",
    map_exists: false,
    created_at: "2026-10-29T10:00:00Z",
    started_at: "2026-10-29T10:00:00Z",
    updated_at: "2026-10-29T10:00:00Z",
    progress: null,
    progress_at: null,
    error: null,
    position: null,
  };
  test("counts from the last progress, else from the start", () => {
    expect(staleMinutes(base, at("2026-10-29T10:09:59Z"))).toBeNull();
    expect(staleMinutes(base, at("2026-10-29T10:12:00Z"))).toBe(12);
    const moved = { ...base, progress: "round 2 of 6", progress_at: "2026-10-29T10:11:00Z" };
    expect(staleMinutes(moved, at("2026-10-29T10:12:00Z"))).toBeNull();
  });
  test("only running jobs go stale", () => {
    expect(staleMinutes({ ...base, status: "queued" }, at("2026-10-29T11:00:00Z"))).toBeNull();
  });
});
```

`frontend/tests/jobspage.test.tsx`, with `mockFetch` and `renderApp("/jobs")` from `./helpers`:

1. With one running fix (`progress: "round 2 of 6"`, `map_exists: true`, `map_id: "m1"`, `title: "Acid Rain"`), two queued jobs (positions 1 and 2) and one failed recent job (`error: "boom"`): the page shows the headings "Running", "Queued", "Recent"; "Acid Rain" links to `/maps/m1`; "round 2 of 6" is visible; "boom" is visible; the Jobs tab shows the count `3`.
2. Pressing "Cancel" on the first queued job sends `DELETE /api/jobs/<id>` (assert on `calls` from `mockFetch`, method from the second handler argument).
3. With an empty list, "Nothing running or queued." shows and the tab has no count.
4. The Library and BeatSaver tabs are still present and the Jobs tab is `aria-current="page"` on `/jobs`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `task st:web:test -- jobtime jobspage`
Expected: FAIL (modules missing).

- [ ] **Step 3: Implement**

`frontend/src/lib/jobtime.ts`:

```ts
// Elapsed and stale times for the Jobs tab.
import type { JobView } from "../api/types";

export const STALE_MS = 10 * 60 * 1000;

export function duration(fromIso: string, toMs: number): string {
  const from = Date.parse(fromIso);
  const s = Number.isFinite(from) ? Math.max(0, Math.floor((toMs - from) / 1000)) : 0;
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min ${s % 60} s`;
  return `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`;
}

/** Minutes without progress for a running job, once past STALE_MS; otherwise null. */
export function staleMinutes(job: JobView, nowMs: number): number | null {
  if (job.status !== "running") return null;
  const since = Date.parse(job.progress_at ?? job.started_at ?? "");
  if (!Number.isFinite(since) || nowMs - since < STALE_MS) return null;
  return Math.floor((nowMs - since) / 60_000);
}
```

`frontend/src/components/SectionTabs.tsx`: extend `active`, add the Jobs item to `ITEMS`, and render the count inside the Jobs link:

```tsx
const count = activeCount(useJobLists());
// inside the Jobs item's link, after the label:
{
  key === "jobs" && count > 0 && (
    <span className="tab-count" aria-label={`${count} active`}>
      {count}
    </span>
  );
}
```

Follow the component's existing map over `ITEMS`. `tests/mapTabsLook.test.tsx` renders `SectionTabs` directly; if it has no `QueryClientProvider`, wrap its renders in one (`new QueryClient()`), changing nothing it asserts.

`frontend/src/pages/JobsPage.tsx`: header reuses the library page header structure (look at `LibraryPage.tsx` lines 36-44 for the wrapper classes) with `<SectionTabs active="jobs" heading="Jobs" headingId="jobs-heading" />`. Body:

```tsx
export function JobsPage() {
  const lists = useJobLists();
  const client = useQueryClient();
  const announce = useAnnounce();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const cancel = async (job: JobView) => {
    try {
      await cancelJob(job.id);
    } catch (err) {
      announce({ variant: "danger", title: `Cancel ${job.title}`, message: errorText(err) });
    }
    await client.invalidateQueries({ queryKey: keys.jobs });
  };
  // three <section aria-labelledby=...> blocks: Running, Queued, Recent;
  // when running and queued are both empty, a <p className="jobs-empty">Nothing running or queued.</p>
  // above Recent; Recent is omitted when empty.
}
```

Row content:

1. Running: title (a `Link` to `/maps/<map_id>` when `map_exists`, else text), kind label, `duration(started_at, now)`, `progress` when set, and when `staleMinutes` returns n: `<span className="jobs-stale">no progress for {n} min</span>`.
2. Queued: `#{position}`, title, kind label, "waiting " + `duration(created_at, now)`, a `Cancel` button (`aria-label={`Cancel ${title}`}` visible text "Cancel").
3. Recent: status icon (reuse the `Icon` names the library chips use for done and failed; `cancelled` uses the muted dot), title, kind label, `duration(started_at ?? created_at, Date.parse(updated_at))`, error text for failed, finished time with `toLocaleTimeString()`.

Kind labels: a `KIND_LABEL` record in the page: scan "Scan", fix "Fix", apply "Apply", crop "Crop", generate "Generate", learn "Learn lightshows", "bs-download" "Download maps". Use `errorText` from wherever the app already formats API errors (search `instanceof ApiError` under `src/lib`); if none, `err instanceof Error ? err.message : String(err)`.

`frontend/src/styles/jobs.css`: a list per section with rows in a grid `minmax(0, 1fr) auto auto` on wide screens, stacking to one column below 720px; `.tab-count` a small pill using `var(--blue)`; `.jobs-stale` in `var(--amber)`; `.jobs-empty` in `var(--muted)`. Import it the same way other page styles are imported (search `import "../styles/` in `src/pages`).

`frontend/src/App.tsx`:

```tsx
const JobsPage = lazyRoute(() => import("./pages/JobsPage").then((m) => ({ default: m.JobsPage })));
// in routes, after /beatsaver:
{ path: "/jobs", element: <JobsPage />, errorElement: <RouteError /> },
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `task st:web:test` then `task st:web:check`
Expected: PASS.

- [ ] **Step 5: README and commit**

Add rows for `JobsPage.tsx`, `jobtime.ts`, `jobs.css`; update the `SectionTabs.tsx` row to "Library | BeatSaver | Jobs tabs ... with the active job count". Main thread commits: `task st:commit -- -m "feat(web): Jobs tab with running, queued and recent jobs, cancel and stale warnings" <files>`

---
