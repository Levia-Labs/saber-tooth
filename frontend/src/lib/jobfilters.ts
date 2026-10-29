// Jobs table state: URL encoding, client-side filter and sort. Every URL value is whitelisted.
import type { JobKind, JobLists, JobState, JobView } from "../api/types";
import { KIND_ORDER } from "./jobkinds";

export const JOB_STATES: readonly JobState[] = ["running", "queued", "done", "failed", "cancelled"];
export const JOB_SORTS = ["status", "title", "length", "created"] as const;
export type JobSort = (typeof JOB_SORTS)[number];

export interface JobsState {
  status: JobState[];
  kind: JobKind[];
  q: string;
  sort: JobSort;
  ascending: boolean;
}

export const DEFAULT_JOBS_STATE: JobsState = {
  status: [],
  kind: [],
  q: "",
  sort: "status",
  ascending: true,
};

const MAX_Q = 200;

const pick = <T extends string>(text: string | null, allowed: readonly T[]): T[] => {
  const given = new Set((text ?? "").split(","));
  return allowed.filter((a) => given.has(a));
};

export function parseJobsState(search: string): JobsState {
  const p = new URLSearchParams(search);
  const sort = p.get("sort");
  return {
    status: pick(p.get("status"), JOB_STATES),
    kind: pick(p.get("kind"), KIND_ORDER),
    q: (p.get("q") ?? "").slice(0, MAX_Q),
    sort: JOB_SORTS.find((s) => s === sort) ?? "status",
    ascending: p.get("dir") !== "desc",
  };
}

export function encodeJobsState(state: JobsState): URLSearchParams {
  const p = new URLSearchParams();
  if (state.status.length) p.set("status", state.status.join(","));
  if (state.kind.length) p.set("kind", state.kind.join(","));
  if (state.q) p.set("q", state.q);
  if (state.sort !== "status") p.set("sort", state.sort);
  if (!state.ascending) p.set("dir", "desc");
  return p;
}

export const jobsFilterCount = (s: JobsState) => ({
  status: s.status.length,
  kind: s.kind.length,
  title: s.q ? 1 : 0,
});

export const clearJobFilters = (s: JobsState): JobsState => ({
  ...s,
  status: [],
  kind: [],
  q: "",
});

export const allJobs = (lists: JobLists): JobView[] => [
  ...lists.running,
  ...lists.queued,
  ...lists.recent,
];

export function filterJobs(jobs: JobView[], s: JobsState): JobView[] {
  const q = s.q.trim().toLowerCase();
  return jobs.filter(
    (j) =>
      (s.status.length === 0 || s.status.includes(j.status)) &&
      (s.kind.length === 0 || s.kind.includes(j.kind)) &&
      (q === "" || j.title.toLowerCase().includes(q)),
  );
}

/** Milliseconds a job has run: to `now` while running, to its last update once finished, else null. */
export function jobLengthMs(job: JobView, now: number): number | null {
  if (job.status === "queued") return null;
  const from = Date.parse(job.started_at ?? job.created_at);
  const to = job.status === "running" ? now : Date.parse(job.updated_at);
  return Number.isFinite(from) && Number.isFinite(to) ? Math.max(0, to - from) : null;
}

const ms = (iso: string | null) => {
  const t = Date.parse(iso ?? "");
  return Number.isFinite(t) ? t : 0;
};

/** Running, then queued by position, then finished with the latest first. */
function byStatus(a: JobView, b: JobView): number {
  const rank = (j: JobView) => (j.status === "running" ? 0 : j.status === "queued" ? 1 : 2);
  if (rank(a) !== rank(b)) return rank(a) - rank(b);
  if (a.status === "running")
    return ms(a.started_at ?? a.created_at) - ms(b.started_at ?? b.created_at);
  if (a.status === "queued") return (a.position ?? 0) - (b.position ?? 0);
  return ms(b.updated_at) - ms(a.updated_at);
}

export function sortJobs(jobs: JobView[], s: JobsState, now: number): JobView[] {
  const dir = s.ascending ? 1 : -1;
  const compare = (a: JobView, b: JobView): number => {
    if (s.sort === "title") return dir * a.title.localeCompare(b.title);
    if (s.sort === "created") return dir * (ms(a.created_at) - ms(b.created_at));
    if (s.sort === "length") {
      const x = jobLengthMs(a, now);
      const y = jobLengthMs(b, now);
      if (x === null || y === null) return x === y ? 0 : x === null ? 1 : -1;
      return dir * (x - y);
    }
    return dir * byStatus(a, b);
  };
  return jobs
    .map((job, i) => ({ job, i }))
    .sort((a, b) => compare(a.job, b.job) || a.i - b.i)
    .map((e) => e.job);
}
