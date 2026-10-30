// Start a job and poll it until it ends; used by learn, generate and the map page actions.
import { useCallback, useEffect, useRef, useState } from "react";
import { useAnnounce } from "../components/Announcer";
import type { AnnounceInput } from "../lib/announcements";
import { errorText, progressReporter, useOpenJobs } from "../lib/jobtoasts";
import { getJob, request, isRetryable, type Started } from "./client";
import type { Job, JobView } from "./types";

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

const watched = new Map<string, number>(); // live pollJob calls per id
/** Ids a live pollJob is polling; the toast watcher leaves these to their page. */
export const watchedJobs: { has(id: string): boolean } = { has: (id) => watched.has(id) };

const settled = new Set<string>(); // ids whose poll ended on a server verdict, for this session
/** Ids the toast watcher must not adopt: being polled now, or already finished by their page. */
export const ownedJobs: { has(id: string): boolean } = {
  has: (id) => watched.has(id) || settled.has(id),
};

/** onStatus text once the server has failed to answer MAX_FETCH_FAILS times in a row. */
export const UNREACHABLE = "unreachable";

/**
 * Poll a job to its end with backoff to 3 s. It never gives up while the server reports the job
 * queued or running, and never on an unreachable server (it reports `UNREACHABLE` once and keeps
 * trying); only a server verdict (done, failed, cancelled), an abort or a non-retryable error ends it.
 */
export async function pollJob(
  jobId: string,
  signal: AbortSignal,
  onStatus: (status: string, job?: Job) => void,
): Promise<Job> {
  watched.set(jobId, (watched.get(jobId) ?? 0) + 1);
  try {
    let delay = FIRST_DELAY_MS;
    let fails = 0;
    let last: Job | undefined; // the last job the server reported, kept so a retry keeps the cancel_requested state
    while (!signal.aborted) {
      try {
        const job = await getJob(jobId);
        last = job;
        fails = 0;
        if (job.status === "done" || job.status === "failed" || job.status === "cancelled") {
          settled.add(jobId); // the page announces this end; a stale list must not re-announce it
        }
        if (job.status === "done") return job;
        if (job.status === "failed") throw new JobFailed(job.error ?? "job failed", job);
        if (job.status === "cancelled") throw new JobFailed("cancelled", job);
        onStatus(
          job.status === "queued" && job.position ? `queued, position ${job.position}` : job.status,
          job,
        );
      } catch (err) {
        if (err instanceof JobFailed) throw err;
        fails += 1;
        if (!isRetryable(err)) throw err;
        // Unreachable is not a verdict: the job may still run, so keep polling and report once.
        if (fails === MAX_FETCH_FAILS) onStatus(UNREACHABLE, last);
        else if (fails < MAX_FETCH_FAILS) onStatus(`retrying (${fails}/${MAX_FETCH_FAILS})`, last);
      }
      await sleep(delay, signal);
      delay = Math.min(delay * 1.5, MAX_DELAY_MS);
    }
    throw new JobFailed("cancelled");
  } finally {
    const left = (watched.get(jobId) ?? 1) - 1;
    if (left > 0) watched.set(jobId, left);
    else watched.delete(jobId);
  }
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
  const open = useOpenJobs();
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
      try {
        const started = await start();
        // No toast while the job is queued; the first one appears when it runs.
        const report = progressReporter(announce, { key, title: label, jobId: started.job, open });
        const done = await pollJob(started.job, ctl.signal, (s, polled) => {
          if (s.startsWith("queued")) return;
          if (s === UNREACHABLE) {
            announce({
              key,
              variant: "warning",
              title: label,
              message:
                "The server is unreachable, so the state of this job is unknown. Waiting for it to answer.",
            });
            return;
          }
          report(s, polled);
        });
        setJob(done);
        setState("done");
        announce({ key, variant: "success", title: label, message: "Done", onOpen: open });
        return done;
      } catch (err) {
        // Ended by our own abort (the page unmounted): the job still runs; the toast watcher owns it.
        if (ctl.signal.aborted) return null;
        const message = errorText(err);
        if (err instanceof JobFailed && err.job) setJob(err.job);
        setError(message);
        setState("failed");
        const cancelled = err instanceof JobFailed && err.job?.status === "cancelled";
        announce({
          key,
          variant: cancelled ? "info" : "danger",
          title: label,
          message: cancelled ? "Cancelled" : message,
          onOpen: open,
        });
        return null;
      } finally {
        running.current = false;
      }
    },
    [announce, label, key, open],
  );

  return { state, busy: state === "running", error, job, run };
}

/**
 * Start a job and follow it with a keyed progress toast (none while queued, self-closing, stays closed
 * once closed). Resolves with the finished job; throws what `start` or `pollJob` throws.
 */
export async function runAnnounced(
  announce: (input: AnnounceInput) => void,
  start: () => Promise<Started>,
  { key, title }: { key: string; title: string },
): Promise<Job> {
  const started = await start();
  const report = progressReporter(announce, { key, title, jobId: started.job });
  return pollJob(started.job, new AbortController().signal, report);
}

/** Re-queue a failed job; resolves with the new queued job's view (409 when it is not failed). */
export const retryJob = (id: string): Promise<JobView> =>
  request("POST", `/api/jobs/${encodeURIComponent(id)}/retry`);
