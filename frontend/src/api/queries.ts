// TanStack Query hooks and cache helpers for the library, one map and jobs.
import {
  useInfiniteQuery,
  useQueries,
  useQuery,
  useQueryClient,
  type InfiniteData,
  type QueryClient,
} from "@tanstack/react-query";
import { useEffect } from "react";
import type { LibraryState } from "../lib/urlstate";
import { isRunning } from "../lib/status";
import { getFacets, getJob, getMap, getProposals, isRetryable, listMaps } from "./client";
import type { Job, MapItem, MapPage } from "./types";

export const keys = {
  maps: ["maps"] as const,
  library: (state: LibraryState) => ["maps", "library", state] as const,
  facets: ["maps", "facets"] as const,
  map: (id: string) => ["maps", "item", id] as const,
  proposals: (id: string) => ["proposals", id] as const,
  job: (id: string) => ["job", id] as const,
};

export const JOB_POLL_MS = 2000;
export const retry = (count: number, err: unknown): boolean => count < 2 && isRetryable(err);

export function useLibrary(state: LibraryState) {
  return useInfiniteQuery({
    queryKey: keys.library(state),
    queryFn: ({ pageParam, signal }) => listMaps(state, pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (last: MapPage, pages) => {
      const loaded = pages.reduce((n, p) => n + p.items.length, 0);
      return last.items.length > 0 && loaded < last.total ? loaded : undefined;
    },
    retry,
  });
}

export function useFacets() {
  return useQuery({ queryKey: keys.facets, queryFn: ({ signal }) => getFacets(signal), retry });
}

export function useMap(id: string) {
  return useQuery({ queryKey: keys.map(id), queryFn: () => getMap(id), retry });
}

export function useProposals(id: string) {
  return useQuery({ queryKey: keys.proposals(id), queryFn: () => getProposals(id), retry });
}

/** Replace one item in every cached library page (and the single-item cache). */
export function patchMap(client: QueryClient, item: MapItem): void {
  client.setQueriesData<InfiniteData<MapPage>>({ queryKey: ["maps", "library"] }, (data) =>
    data
      ? {
          ...data,
          pages: data.pages.map((p) => ({
            ...p,
            items: p.items.map((m) => (m.id === item.id ? item : m)),
          })),
        }
      : data,
  );
  client.setQueryData(keys.map(item.id), item);
}

/** Show a job on a row at once, before the server list reflects it. */
export function markRunning(
  client: QueryClient,
  item: MapItem,
  kind: "scan" | "apply",
  id: string,
) {
  patchMap(client, {
    ...item,
    status: "queued",
    job: { id, kind, status: "queued" },
  });
}

/**
 * Poll the jobs of rows that show a running status every 2 s; when a job ends, refetch that
 * row in place and refresh the facet counts. Stops by itself when no row is running.
 */
export function useLiveRows(items: MapItem[]): void {
  const client = useQueryClient();
  const running = items.filter((m) => isRunning(m.status) && m.job);
  const results = useQueries({
    queries: running.map((m) => ({
      queryKey: keys.job(m.job?.id ?? ""),
      queryFn: () => getJob(m.job?.id ?? ""),
      refetchInterval: (q: { state: { data: Job | undefined } }) => {
        const s = q.state.data?.status;
        return s === "done" || s === "failed" ? false : JOB_POLL_MS;
      },
      retry,
    })),
  });
  const finished = running
    .filter((_, i) => {
      const s = results[i]?.data?.status;
      return s === "done" || s === "failed";
    })
    .map((m) => m.id)
    .join(",");
  useEffect(() => {
    if (!finished) return;
    for (const id of finished.split(",")) {
      void getMap(id).then((fresh) => patchMap(client, fresh));
    }
    void client.invalidateQueries({ queryKey: keys.facets });
  }, [finished, client]);
}
