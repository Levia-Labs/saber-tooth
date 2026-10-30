// How a job reads on the Jobs page and in toasts: status chips and tags, fix rounds, elapsed and stale times.
import type { JobState, JobView, StatusKey } from "../api/types";
import type { IconName } from "../components/icons";

// Fix rounds, read from the job's progress text "round n of m"; null when the text has none.
const ROUND = /\bround (\d{1,4}) of (\d{1,4})\b/i;

/** "n/m" for a progress text such as "round 2 of 6", or null when the rounds are not known. */
export function roundsText(progress: string | null | undefined): string | null {
  const hit = ROUND.exec(progress ?? "");
  return hit ? `${Number(hit[1])}/${Number(hit[2])}` : null;
}

/** Rounds of a job for display: none once it is done (done means all of them), else how far it got. */
export function jobRounds(job: { status: string; progress: string | null }): string | null {
  return job.status === "done" ? null : roundsText(job.progress);
}

/** The library chip a job state borrows: its icon and colour. */
const CHIP: Record<JobState, StatusKey> = {
  running: "fixing",
  queued: "queued",
  done: "ok",
  failed: "error",
  cancelled: "unscanned",
};

/** One icon per state: spinner running, clock queued, check done, X failed, trash cancelled. */
const ICON: Record<JobState, IconName> = {
  running: "spinner",
  queued: "clock",
  done: "ok",
  failed: "reject",
  cancelled: "trash",
};

const WORD: Record<JobState, string> = {
  running: "Running",
  queued: "Queued",
  done: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

export const jobIcon = (job: Pick<JobView, "status">): IconName => ICON[job.status];

export const jobChip = (job: Pick<JobView, "status">): StatusKey => CHIP[job.status];

/** Tooltip and aria text of a job's status chip. */
export function jobStatusLabel(job: Pick<JobView, "status" | "cancel_requested">): string {
  return job.status === "running" && job.cancel_requested ? "Cancelling" : WORD[job.status];
}

export interface JobTag {
  text: string;
  /** info: the queue position; warning: the fix rounds. */
  tone: "info" | "warning";
  /** Spoken form, appended to the status word. */
  label: string;
}

/** The detail shown inside the status widget: #n when queued, x/y rounds otherwise (never when done). */
export function jobTag(job: Pick<JobView, "status" | "position" | "progress">): JobTag | null {
  if (job.status === "queued") {
    return job.position
      ? { text: `#${job.position}`, tone: "info", label: `position ${job.position}` }
      : null;
  }
  const rounds = jobRounds(job);
  if (!rounds) return null;
  return { text: rounds, tone: "warning", label: `round ${rounds.replace("/", " of ")}` };
}

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
