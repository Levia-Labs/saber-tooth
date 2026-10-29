// Which job toasts to show, given the server's job list; pure so it is tested without React.
// A job gets a toast only once it runs; queued jobs have none, only a row on the Jobs tab.
import type { JobLists, JobView } from "../api/types";
import { capitalize, type AnnounceInput, type BannerAction } from "./announcements";
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
  job.cancel_requested ? "Cancelling" : capitalize(job.progress ?? "running");

/** The Cancel button of a running toast; while the stop is pending it reads Cancelling and is disabled. */
export function cancelAction(requested: boolean, onClick: () => void): BannerAction {
  return {
    label: requested ? "Cancelling" : "Cancel",
    icon: requested ? "spinner" : "stop",
    disabled: requested,
    keepOpen: true,
    onClick,
  };
}

export type Tracked = Map<string, { key: string; message: string }>;

export interface ToastPlan {
  show: AnnounceInput[];
  withdraw: string[];
  next: Tracked;
  summary: { running: number } | null;
}

export function planToasts(
  prev: ReadonlyMap<string, { key: string; message: string }>,
  lists: JobLists,
  owned: { has(id: string): boolean },
  onCancel?: (job: JobView) => void,
  /** Ids whose progress toast the user closed; it stays closed across message changes, only the outcome shows. */
  dismissed?: Set<string>,
): ToastPlan {
  const active = lists.running.filter((j) => !owned.has(j.id));
  const folded = active.length > SUMMARY_ABOVE;
  const show: AnnounceInput[] = [];
  const withdraw: string[] = [];
  const next: Tracked = new Map();
  for (const job of active) {
    const key = toastKey(job);
    const message = activeMessage(job);
    // A folded job is tracked with an empty message so it is announced again once the summary unfolds.
    next.set(job.id, { key, message: folded ? "" : message });
    if (dismissed?.has(job.id)) continue;
    if (folded) {
      if (prev.get(job.id)?.message) withdraw.push(key);
    } else if (prev.get(job.id)?.message !== message) {
      const toast: AnnounceInput = { key, variant: "progress", title: toastTitle(job), message };
      if (dismissed) toast.onDismiss = () => dismissed.add(job.id);
      if (onCancel) toast.actions = [cancelAction(job.cancel_requested, () => onCancel(job))];
      show.push(toast);
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
    const base = { key: toastKey(job), title: toastTitle(job) };
    if (job.status === "failed") {
      show.push({ ...base, variant: "danger", message: job.error ?? "failed" });
    } else if (job.status === "cancelled") {
      show.push({ ...base, variant: "info", message: "Cancelled" });
    } else if (job.status === "done" && !folded) {
      show.push({ ...base, variant: "success", message: "Done" });
    } else {
      withdraw.push(base.key);
    }
  }
  const summary = folded ? { running: active.length } : null;
  if (summary) {
    show.push({ key: SUMMARY_KEY, variant: "progress", title: `${summary.running} running` });
  }
  return { show, withdraw, next, summary };
}
