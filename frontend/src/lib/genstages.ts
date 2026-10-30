import type { JobState } from "../api/types";

// The stages of a generate job, derived from the job's status and progress text.
export type StageState = "done" | "now" | "todo" | "failed";
export interface Stage {
  label: string;
  state: StageState;
}
export interface StageJob {
  status: JobState;
  progress?: string | null | undefined;
  position?: number | null | undefined;
}

const LABELS = ["Download", "Analyse beats", "Map", "Fix", "Write"] as const;
/** Progress words the server reports (service/generate.py) and the stage each one starts. */
const STARTS: [string, number][] = [
  ["analysing", 1],
  ["building", 2],
  ["fixing", 3],
  ["saving", 4],
];

function current(job: StageJob): number {
  const text = (job.progress ?? "").toLowerCase();
  return STARTS.find(([word]) => text.startsWith(word))?.[1] ?? 0;
}

/** The five stages with their state; a file upload names the first one Upload. */
export function stageStates(job: StageJob, source: "url" | "file"): Stage[] {
  const at = job.status === "done" ? LABELS.length : job.status === "queued" ? -1 : current(job);
  const ended = job.status === "failed" || job.status === "cancelled";
  return LABELS.map((label, index) => {
    const state: StageState =
      index < at ? "done" : index === at ? (ended ? "failed" : "now") : "todo";
    return { label: index === 0 && source === "file" ? "Upload" : label, state };
  });
}
