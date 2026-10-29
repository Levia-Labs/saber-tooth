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
