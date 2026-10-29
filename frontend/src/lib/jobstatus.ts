// Job states shown as the library's status chips: the same icon box, colours and tooltip.
import type { JobState, JobView, StatusKey } from "../api/types";
import type { IconName } from "../components/icons";

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

export const jobIcon = (job: Pick<JobView, "status">): IconName => ICON[job.status];

const WORD: Record<JobState, string> = {
  running: "Running",
  queued: "Queued",
  done: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

export const jobChip = (job: Pick<JobView, "status">): StatusKey => CHIP[job.status];

/** Tooltip and aria text of a job's status chip. */
export function jobStatusLabel(job: Pick<JobView, "status" | "cancel_requested">): string {
  return job.status === "running" && job.cancel_requested ? "Cancelling" : WORD[job.status];
}
