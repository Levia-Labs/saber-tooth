// The one-click Fix: start the job, follow it, and report the outcome as a toast.
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useAnnounce } from "../components/Announcer";
import { fixKey, fixToast } from "../lib/fixToast";
import { errorText } from "../lib/jobtoasts";
import { fixMap } from "./client";
import { JobFailed, runAnnounced } from "./jobs";
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
    const start = async () => {
      const started = await fixMap(item.id);
      markRunning(client, item, "fix", started.job);
      // Refetch with the current filters so a map that is now queued leaves a view that excludes it.
      void client.invalidateQueries({ queryKey: ["maps", "library"] });
      return started;
    };
    try {
      const job = await runAnnounced(announce, start, {
        key: fixKey(item.id),
        title: `Fix ${name}`,
      });
      announce(fixToast(item.id, name, job, null));
    } catch (err) {
      announce(fixToast(item.id, name, err instanceof JobFailed ? err.job : null, errorText(err)));
    }
    await refresh(client, item.id);
  }, [client, announce, item, name]);
}
