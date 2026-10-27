import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import {
  downloadMaps,
  outcomes,
  refreshAfterDownload,
  type BsMap,
  type BsOutcome,
} from "../../api/beatsaver";
import { useJobRunner, type JobRunner } from "../../api/jobs";

export type RowStatus =
  | { kind: "none" }
  | { kind: "installed" }
  | { kind: "downloading" }
  | { kind: "failed"; reason: string };

export interface Downloads {
  runner: JobRunner;
  pending: ReadonlySet<string>;
  results: Readonly<Record<string, BsOutcome>>;
  start: (ids: string[]) => Promise<void>;
  status: (item: BsMap) => RowStatus;
}

/** Runs download jobs and remembers per-map progress and outcomes for the rows. */
export function useDownloads(): Downloads {
  const runner = useJobRunner("Download maps");
  const client = useQueryClient();
  const [pending, setPending] = useState<ReadonlySet<string>>(new Set());
  const [results, setResults] = useState<Record<string, BsOutcome>>({});
  const { busy, run } = runner;

  const start = useCallback(
    async (ids: string[]) => {
      if (busy || !ids.length) return;
      setPending(new Set(ids));
      setResults({});
      const job = await run(() => downloadMaps(ids));
      setPending(new Set());
      const done = job ? outcomes(job.result) : [];
      const seen = new Set(done.map((o) => o.id));
      const lost: BsOutcome[] = job
        ? []
        : ids.map((id) => ({ id, status: "failed", reason: "The download job failed." }));
      const missing: BsOutcome[] = job
        ? ids
            .filter((id) => !seen.has(id))
            .map((id) => ({ id, status: "failed", reason: "No result reported." }))
        : [];
      setResults(Object.fromEntries([...done, ...lost, ...missing].map((o) => [o.id, o])));
      refreshAfterDownload(client);
    },
    [busy, run, client],
  );

  const status = useCallback(
    (item: BsMap): RowStatus => {
      if (pending.has(item.id)) return { kind: "downloading" };
      const out = results[item.id];
      if (out?.status === "failed") {
        return { kind: "failed", reason: out.reason ?? "Download failed." };
      }
      if (item.installed || out) return { kind: "installed" };
      return { kind: "none" };
    },
    [pending, results],
  );

  return { runner, pending, results, start, status };
}

export interface Tally {
  installed: number;
  skipped: number;
  failed: number;
}

export function tally(results: Readonly<Record<string, BsOutcome>>): Tally {
  const t: Tally = { installed: 0, skipped: 0, failed: 0 };
  for (const o of Object.values(results)) t[o.status] += 1;
  return t;
}
