// The one-click Fix: start the job, follow it, and report the outcome as a toast.
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useAnnounce } from "../components/Announcer";
import { capitalize } from "../lib/announcements";
import { fixKey, fixToast } from "../lib/fixToast";
import { dismissedJobs } from "../lib/jobdismiss";
import { fixMap } from "./client";
import { JobFailed, pollJob } from "./jobs";
import { keys, markRunning } from "./queries";
import type { MapItem } from "./types";

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
    const key = fixKey(item.id);
    const title = `Fix ${name}`;
    try {
      const started = await fixMap(item.id);
      markRunning(client, item, "fix", started.job);
      // Refetch with the current filters so a map that is now queued leaves a view that excludes it.
      void client.invalidateQueries({ queryKey: ["maps", "library"] });
      // No toast while queued; one appears when the job runs, closes by itself and stays closed once closed.
      const job = await pollJob(started.job, new AbortController().signal, (s) => {
        if (s.startsWith("queued") || dismissedJobs.has(started.job)) return;
        announce({
          key,
          variant: "progress",
          title,
          message: capitalize(s),
          autoClose: true,
          onDismiss: () => dismissedJobs.add(started.job),
        });
      });
      announce(fixToast(item.id, name, job, null));
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      announce(fixToast(item.id, name, err instanceof JobFailed ? err.job : null, message));
    }
    await refresh(client, item.id);
  }, [client, announce, item, name]);
}
