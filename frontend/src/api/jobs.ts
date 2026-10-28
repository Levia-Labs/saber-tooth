// Start a job and poll it until it ends; used by learn, generate and the map page actions.
import { useCallback, useEffect, useRef, useState } from "react";
import { useAnnounce } from "../components/Announcer";
import { capitalize } from "../lib/announcements";
import { getJob, isRetryable, type Started } from "./client";
import type { Job } from "./types";

const MAX_JOB_MS = 30 * 60 * 1000;
const MAX_FETCH_FAILS = 3;
const FIRST_DELAY_MS = 1000;
const MAX_DELAY_MS = 3000;

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      resolve();
    });
  });

export class JobFailed extends Error {
  readonly job: Job | null;
  constructor(message: string, job: Job | null = null) {
    super(message);
    this.name = "JobFailed";
    this.job = job;
  }
}

/** Poll a job until done or failed with backoff to 3 s; gives up after 30 minutes. */
export async function pollJob(
  jobId: string,
  signal: AbortSignal,
  onStatus: (status: string) => void,
): Promise<Job> {
  const deadline = Date.now() + MAX_JOB_MS;
  let delay = FIRST_DELAY_MS;
  let fails = 0;
  while (Date.now() < deadline && !signal.aborted) {
    try {
      const job = await getJob(jobId);
      fails = 0;
      if (job.status === "done") return job;
      if (job.status === "failed") throw new JobFailed(job.error ?? "job failed", job);
      onStatus(job.status);
    } catch (err) {
      if (err instanceof JobFailed) throw err;
      fails += 1;
      if (!isRetryable(err) || fails >= MAX_FETCH_FAILS) throw err;
      onStatus(`retrying (${fails}/${MAX_FETCH_FAILS})`);
    }
    await sleep(delay, signal);
    delay = Math.min(delay * 1.5, MAX_DELAY_MS);
  }
  if (signal.aborted) throw new JobFailed("cancelled");
  throw new JobFailed("timed out after 30 minutes");
}

export type RunState = "idle" | "running" | "done" | "failed";

export interface JobRunner {
  state: RunState;
  busy: boolean;
  error: string | null;
  job: Job | null;
  /** Start and follow a job; resolves with the finished job, or null when it failed. */
  run: (start: () => Promise<Started>) => Promise<Job | null>;
}

/** Runs one job at a time, announcing progress with the given label; `key` (default the label) names its toast, so give per-map jobs a key with the map id. */
export function useJobRunner(label: string, key: string = label): JobRunner {
  const announce = useAnnounce();
  const [state, setState] = useState<RunState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const abort = useRef<AbortController | null>(null);
  const running = useRef(false);

  useEffect(() => () => abort.current?.abort(), []);

  const run = useCallback(
    async (start: () => Promise<Started>): Promise<Job | null> => {
      if (running.current) return null;
      running.current = true;
      const ctl = new AbortController();
      abort.current = ctl;
      setState("running");
      setError(null);
      setJob(null);
      announce({ key, variant: "progress", title: label, message: "Queued" });
      try {
        const started = await start();
        const done = await pollJob(started.job, ctl.signal, (s) =>
          announce({ key, variant: "progress", title: label, message: capitalize(s) }),
        );
        setJob(done);
        setState("done");
        announce({ key, variant: "success", title: label, message: "Done" });
        return done;
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        if (err instanceof JobFailed && err.job) setJob(err.job);
        setError(message);
        setState("failed");
        announce({ key, variant: "danger", title: label, message });
        return null;
      } finally {
        running.current = false;
      }
    },
    [announce, label, key],
  );

  return { state, busy: state === "running", error, job, run };
}
