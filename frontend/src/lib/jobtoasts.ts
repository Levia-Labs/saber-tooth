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
  owned: { has(id: string): boolean },
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
