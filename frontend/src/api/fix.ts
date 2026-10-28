// The one-click Fix: start the job, follow it, and keep its outcome for the alerts.
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";
import { useAnnounce } from "../components/Announcer";
import { capitalize } from "../lib/announcements";
import { fixMap } from "./client";
import { JobFailed, pollJob } from "./jobs";
import { keys, markRunning } from "./queries";
import type { Job, MapItem } from "./types";

export interface FixOutcome {
  key: number;
  mapId: string;
  name: string;
  job: Job | null;
  error: string | null;
}

let outcomes: readonly FixOutcome[] = [];
let counter = 0;
const listeners = new Set<() => void>();

function publish(next: readonly FixOutcome[]) {
  outcomes = next;
  listeners.forEach((fn) => fn());
}

export function dismissFix(key: number) {
  publish(outcomes.filter((o) => o.key !== key));
}

/** Test hook: forget every outcome. */
export function clearFixOutcomes() {
  publish([]);
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => void listeners.delete(fn);
}

/** Outcomes of finished fixes, newest first; pass a map id to see that map's only. */
export function useFixOutcomes(mapId?: string): readonly FixOutcome[] {
  const all = useSyncExternalStore(subscribe, () => outcomes);
  return mapId === undefined ? all : all.filter((o) => o.mapId === mapId);
}

async function refresh(client: QueryClient, mapId: string) {
  await client.invalidateQueries({ queryKey: ["maps", "library"] });
  await client.invalidateQueries({ queryKey: keys.facets });
  await client.invalidateQueries({ queryKey: keys.map(mapId) });
}

/** Starts a fix on one map; the row shows `fixing` while it runs. */
export function useFix(item: MapItem, name: string): () => Promise<void> {
  const client = useQueryClient();
  const announce = useAnnounce();
  return useCallback(async () => {
    const entry = { key: ++counter, mapId: item.id, name };
    publish(outcomes.filter((o) => o.mapId !== item.id));
    announce({ variant: "progress", title: `Fix ${name}`, message: "Queued" });
    try {
      const started = await fixMap(item.id);
      markRunning(client, item, "fix", started.job);
      const job = await pollJob(started.job, new AbortController().signal, (s) =>
        announce({ variant: "progress", title: `Fix ${name}`, message: capitalize(s) }),
      );
      publish([{ ...entry, job, error: null }, ...outcomes]);
      announce({ variant: "success", title: `Fix ${name}`, message: "Done" });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const job = err instanceof JobFailed ? err.job : null;
      publish([{ ...entry, job, error: message }, ...outcomes]);
      announce({ variant: "danger", title: `Fix ${name}`, message });
    }
    await refresh(client, item.id);
  }, [client, announce, item, name]);
}
