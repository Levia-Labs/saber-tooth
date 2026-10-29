### Task 7 (continued): Toasts that survive refresh and navigation

Start: [task-07a.md](task-07a.md).

- [ ] **Step 3: Implement**

`frontend/src/lib/jobtoasts.ts`:

```ts
// Which job toasts to show, given the server's job list; pure so it is tested without React.
import type { JobLists, JobView } from "../api/types";
import { capitalize, type AnnounceInput } from "./announcements";
import { fixKey } from "./fixToast";

export const SUMMARY_KEY = "jobs-summary";
export const SUMMARY_ABOVE = 4;

const LABEL: Record<string, string> = {
  scan: "Scan",
  fix: "Fix",
  apply: "Apply",
  crop: "Crop",
  generate: "Generating",
  learn: "Learn lightshows",
  "bs-download": "Download maps",
};

export function toastKey(job: JobView): string {
  if (job.kind === "fix" && job.map_id) return fixKey(job.map_id);
  if (job.map_id && ["scan", "apply", "crop"].includes(job.kind)) {
    return `${LABEL[job.kind]}:${job.map_id}`;
  }
  if (job.kind === "generate") return `generate-job-${job.id}`;
  return LABEL[job.kind] ?? job.kind;
}

const toastTitle = (job: JobView): string =>
  job.map_id || job.kind === "generate" ? `${LABEL[job.kind] ?? job.kind} ${job.title}` : job.title;

const activeMessage = (job: JobView): string =>
  job.status === "queued"
    ? `Queued, position ${job.position ?? "?"}`
    : capitalize(job.progress ?? "running");

export type Tracked = Map<string, { key: string; message: string }>;

export interface ToastPlan {
  show: AnnounceInput[];
  withdraw: string[];
  next: Tracked;
  summary: { running: number; waiting: number } | null;
}

export function planToasts(
  prev: ReadonlyMap<string, { key: string; message: string }>,
  lists: JobLists,
  owned: ReadonlySet<string>,
): ToastPlan {
  const active = [...lists.running, ...lists.queued].filter((j) => !owned.has(j.id));
  const folded = active.length > SUMMARY_ABOVE;
  const show: AnnounceInput[] = [];
  const withdraw: string[] = [];
  const next: Tracked = new Map();
  for (const job of active) {
    const key = toastKey(job);
    const message = activeMessage(job);
    next.set(job.id, { key, message });
    if (folded) {
      if (prev.has(job.id)) withdraw.push(key);
    } else if (prev.get(job.id)?.message !== message) {
      show.push({ key, variant: "progress", title: toastTitle(job), message });
    }
  }
  const finished = new Map(lists.recent.map((j) => [j.id, j]));
  for (const [id, last] of prev) {
    if (next.has(id) || owned.has(id)) continue;
    const job = finished.get(id);
    if (!job) {
      withdraw.push(last.key); // gone from every list: older than the recent window
      continue;
    }
    if (job.status === "failed") {
      show.push({
        key: toastKey(job),
        variant: "danger",
        title: toastTitle(job),
        message: job.error ?? "failed",
      });
    } else if (job.status === "done" && !folded) {
      show.push({
        key: toastKey(job),
        variant: "success",
        title: toastTitle(job),
        message: "Done",
      });
    } else {
      withdraw.push(toastKey(job));
    }
  }
  const summary = folded ? { running: lists.running.length, waiting: lists.queued.length } : null;
  if (summary) {
    show.push({
      key: SUMMARY_KEY,
      variant: "progress",
      title: `${summary.running} running, ${summary.waiting} waiting`,
    });
  }
  return { show, withdraw, next, summary };
}
```

`frontend/src/components/JobToasts.tsx`:

```tsx
// Restores job toasts after a refresh and takes over jobs whose page went away.
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { useJobLists } from "../api/joblist";
import { watchedJobs } from "../api/jobs";
import { planToasts, SUMMARY_KEY, type ToastPlan } from "../lib/jobtoasts";
import { useAnnounce, useWithdraw } from "./Announcer";

export function JobToasts() {
  const lists = useJobLists();
  const announce = useAnnounce();
  const withdraw = useWithdraw();
  const navigate = useNavigate();
  const prev = useRef<ToastPlan["next"]>(new Map());
  const summaryClosed = useRef(false);
  const shownSummary = useRef<string | null>(null);

  useEffect(() => {
    const plan = planToasts(prev.current, lists, watchedJobs);
    prev.current = plan.next;
    for (const key of plan.withdraw) withdraw(key);
    for (const t of plan.show) {
      if (t.key !== SUMMARY_KEY) {
        announce(t);
        continue;
      }
      if (summaryClosed.current || shownSummary.current === t.title) continue;
      shownSummary.current = t.title;
      announce({
        ...t,
        actions: [{ label: "Show jobs", onClick: () => navigate("/jobs") }],
        onDismiss: () => {
          summaryClosed.current = true;
        },
      });
    }
    if (!plan.summary) {
      summaryClosed.current = false;
      if (shownSummary.current !== null) withdraw(SUMMARY_KEY);
      shownSummary.current = null;
    }
  }, [lists, announce, withdraw, navigate]);

  return null;
}
```

Check `useWithdraw`'s and `BannerAction`'s exact shapes in `components/Announcer.tsx` and `lib/announcements.ts` (an action press closes the toast; that is intended here). Render `<JobToasts />` once in `Shell` (`App.tsx`), inside `AnnouncerProvider` and the router (it calls `useNavigate`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `task st:web:test` then `task st:web:check`
Expected: PASS, whole suite. If an existing test counts fetch calls, filter `/api/jobs` out of that count in the test rather than changing the watcher.

- [ ] **Step 5: README and commit**

Rows for `JobToasts.tsx` ("restores job toasts after a refresh, takes over jobs whose page unmounted, folds more than 4 into one summary") and `jobtoasts.ts`. Main thread commits: `task st:commit -- -m "feat(web): job toasts survive refresh and navigation; more than 4 active jobs fold into one summary" <files>`

---
