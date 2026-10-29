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
