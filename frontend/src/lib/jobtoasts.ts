// Job toasts: which to show from the server's job list (pure, tested without React), the progress
// callback every job-starting path shares, and where a toast click leads.
// A job gets a toast only once it runs; queued jobs have none, only a row on the Jobs tab.
import { useCallback } from "react";
import { useNavigate } from "react-router";
import type { JobLists, JobView } from "../api/types";
import { vrPath } from "../vr/mode";
import { useVrMode } from "../vr/VrMode";
import { capitalize, type AnnounceInput } from "./announcements";
import { fixKey } from "./fixToast";
import { roundsText } from "./jobview";

export const SUMMARY_KEY = "jobs-summary";
export const SUMMARY_ABOVE = 4;

/**
 * Ids of running jobs whose progress toast the user closed or that timed out; one store for the
 * page-started path (progressReporter) and the list watcher (planToasts), so a closed toast stays
 * closed for the session.
 */
export const dismissedJobs = new Set<string>();

/** The message of a thrown value. */
export const errorText = (err: unknown): string =>
  err instanceof Error ? err.message : String(err);

/** Returns a stable function that opens the Jobs page for the current UI mode (the VR twin in the VR shell). */
export function useOpenJobs(): () => void {
  const navigate = useNavigate();
  const { mode } = useVrMode();
  return useCallback(
    () => void navigate(mode === "vr" ? vrPath("/jobs") : "/jobs"),
    [navigate, mode],
  );
}

interface ProgressOptions {
  key: string;
  title: string;
  jobId: string;
  /** Click handler; given, the toast also reads "Cancelling" on a cancel request and shows the fix rounds. */
  open?: () => void;
}

/** The poll callback of a job a page started: no toast while queued or once closed, else a self-closing progress toast. */
export function progressReporter(
  announce: (input: AnnounceInput) => void,
  { key, title, jobId, open }: ProgressOptions,
): (status: string, job?: { cancel_requested?: boolean; progress?: string | null }) => void {
  return (status, job) => {
    if (status.startsWith("queued") || dismissedJobs.has(jobId)) return;
    const rounds = open ? roundsText(job?.progress) : null;
    announce({
      key,
      variant: "progress",
      title,
      message: open && job?.cancel_requested === true ? "Cancelling" : capitalize(status),
      autoClose: true,
      onDismiss: () => dismissedJobs.add(jobId),
      ...(open && { onOpen: open }),
      ...(rounds && { rounds }),
    });
  };
}

const LABEL: Record<string, string> = {
  scan: "Scan",
  fix: "Fix",
  apply: "Apply",
  crop: "Crop",
  relight: "Relight",
  generate: "Generating",
  learn: "Learn lightshows",
  "bs-download": "Download maps",
};

export function toastKey(job: JobView): string {
  if (job.kind === "fix" && job.map_id) return fixKey(job.map_id);
  if (job.map_id && ["scan", "apply", "crop", "relight"].includes(job.kind)) {
    return `${LABEL[job.kind]}:${job.map_id}`;
  }
  if (job.kind === "generate") return `generate-job-${job.id}`;
  return LABEL[job.kind] ?? job.kind;
}

const toastTitle = (job: JobView): string =>
  job.map_id || job.kind === "generate" ? `${LABEL[job.kind] ?? job.kind} ${job.title}` : job.title;

const activeMessage = (job: JobView): string =>
  job.cancel_requested ? "Cancelling" : capitalize(job.progress ?? "running");

export type Tracked = Map<string, { key: string; message: string }>;

export interface ToastPlan {
  show: AnnounceInput[];
  withdraw: string[];
  next: Tracked;
  summary: { running: number } | null;
}

/** What the plan remembers about the summary toast between calls; mutated by planToasts. */
export interface SummaryState {
  /** The user opened or closed the summary; it stays closed until the count drops to 4 or fewer. */
  closed: boolean;
  /** Title of the summary now showing, so an unchanged count is not announced again. */
  shown: string | null;
  /** Removes a toast by key; the summary's click handler needs it. */
  withdraw?: (key: string) => void;
}

export function planToasts(
  prev: ReadonlyMap<string, { key: string; message: string }>,
  lists: JobLists,
  owned: { has(id: string): boolean },
  /** Runs when a job toast body is clicked; the toast is then one row without buttons. */
  open?: () => void,
  /** Ids whose progress toast closed (X or timeout); it stays closed across message changes, only the outcome shows. */
  dismissed: Set<string> = new Set(),
  summaryState: SummaryState = { closed: false, shown: null },
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
    if (dismissed.has(job.id)) continue;
    if (folded) {
      if (prev.get(job.id)?.message) withdraw.push(key);
    } else if (prev.get(job.id)?.message !== message) {
      const toast: AnnounceInput = {
        key,
        variant: "progress",
        title: toastTitle(job),
        message,
        autoClose: true,
        onDismiss: () => dismissed.add(job.id),
      };
      const rounds = roundsText(job.progress);
      if (rounds) toast.rounds = rounds;
      if (open) toast.onOpen = open;
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
    const base: { key: string; title: string; onOpen?: () => void } = {
      key: toastKey(job),
      title: toastTitle(job),
    };
    if (open) base.onOpen = open;
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
    const title = `${summary.running} running`;
    if (!summaryState.closed && summaryState.shown !== title) {
      summaryState.shown = title;
      show.push({
        key: SUMMARY_KEY,
        variant: "progress",
        title,
        // Opening the summary closes it until the count drops to 4 or fewer; so does its close button.
        onOpen: () => {
          summaryState.closed = true;
          summaryState.withdraw?.(SUMMARY_KEY);
          open?.();
        },
        onDismiss: () => {
          summaryState.closed = true;
        },
      });
    }
  } else {
    summaryState.closed = false;
    if (summaryState.shown !== null) withdraw.push(SUMMARY_KEY);
    summaryState.shown = null;
  }
  return { show, withdraw, next, summary };
}
