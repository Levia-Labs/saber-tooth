// BeatSaver API client and query hooks. The response shapes below are the contract with the
// /api/beatsaver/* routes; adjust them here only.
import { useInfiniteQuery, useQuery, type QueryClient } from "@tanstack/react-query";
import { bsApiParams, BS_PAGE_SIZE, type BsState } from "../lib/bsfilters";
import { plApiParams, plFetched, type PlState } from "../lib/plfilters";
import { request, type Started } from "./client";
import { retry } from "./queries";

export interface BsDifficulty {
  /** Level key: Easy, Normal, Hard, Expert or ExpertPlus (Standard characteristic only). */
  difficulty: string;
  nps: number;
  njs: number;
}

export interface BsMap {
  id: string;
  name: string;
  song: string;
  mapper: string;
  cover_url: string | null;
  preview_url: string | null;
  bpm: number | null;
  /** Seconds. */
  duration: number | null;
  /** Fraction 0 to 1. */
  rating: number;
  upvotes: number;
  downvotes: number;
  tags: string[];
  ranked: boolean;
  difficulties: BsDifficulty[];
  installed: boolean;
  library_id: string | null;
}

/** A page of matches: `cursor` is null at the end; `retry_after` (seconds) is set when
 * BeatSaver rate limited the scan and the items are partial. */
export interface BsPage {
  items: BsMap[];
  cursor: string | null;
  scanned: number;
  matched: number;
  partial?: boolean;
  retry_after?: number | null;
}

export interface BsPlaylist {
  id: string;
  name: string;
  owner: string;
  description?: string;
  cover_url: string | null;
  map_count: number;
  mapper_count: number;
  /** Total playing time in seconds. */
  duration: number;
  upvotes: number;
  downvotes: number;
  /** Fraction 0 to 1: BeatSaver's score, else upvotes over all votes. */
  rating: number;
  min_nps: number;
  max_nps: number;
  /** ISO timestamp. */
  created_at: string;
  curated: boolean;
}

export interface BsPlaylistPage {
  items: BsPlaylist[];
  cursor: string | null;
}

/** Playlist detail: the playlist and one page of its maps with the local filters applied. */
export interface BsPlaylistMaps extends BsPage {
  playlist: BsPlaylist;
}

export interface BsPreset {
  id: number | string;
  name: string;
  /** The filters as URL query keys, see `presetFilters`. */
  filters: Record<string, string>;
  seeded?: boolean;
}

export interface BsConfig {
  playlists_enabled: boolean;
}

export interface BsOutcome {
  id: string;
  status: "installed" | "skipped" | "failed";
  reason?: string | null;
  folder?: string | null;
}

const seg = encodeURIComponent;
const base = "/api/beatsaver";

export const searchMaps = (
  state: BsState,
  cursor: string | null,
  signal?: AbortSignal,
): Promise<BsPage> =>
  request("GET", `${base}/search?${bsApiParams(state, cursor, BS_PAGE_SIZE)}`, undefined, signal);

export const searchPlaylists = (
  state: PlState,
  cursor: string | null,
  signal?: AbortSignal,
): Promise<BsPlaylistPage> =>
  request("GET", `${base}/playlists/search?${plApiParams(state, cursor)}`, undefined, signal);

export const getPlaylistMaps = (
  id: string,
  state: BsState,
  cursor: string | null,
  signal?: AbortSignal,
): Promise<BsPlaylistMaps> =>
  request(
    "GET",
    `${base}/playlists/${seg(id)}?${bsApiParams(state, cursor, BS_PAGE_SIZE)}`,
    undefined,
    signal,
  );

export const getBsConfig = (signal?: AbortSignal): Promise<BsConfig> =>
  request("GET", `${base}/config`, undefined, signal);

export const listPresets = (signal?: AbortSignal): Promise<BsPreset[]> =>
  request("GET", `${base}/presets`, undefined, signal);

export const savePreset = (name: string, filters: Record<string, string>): Promise<BsPreset> =>
  request("POST", `${base}/presets`, { name, filters });

export const deletePreset = (id: number | string): Promise<unknown> =>
  request("DELETE", `${base}/presets/${seg(String(id))}`);

export const downloadMaps = (ids: string[]): Promise<Started> =>
  request("POST", `${base}/download`, { ids });

export const exportPlaylist = (title: string, ids: string[]): Promise<{ path: string }> =>
  request("POST", `${base}/playlist-export`, { title, ids });

/** Per-map results of a finished download job; tolerant of a missing or malformed result. */
export function outcomes(result: Record<string, unknown> | null | undefined): BsOutcome[] {
  const list = result?.["results"] ?? result?.["maps"];
  if (!Array.isArray(list)) return [];
  return list.filter(
    (o): o is BsOutcome => typeof o === "object" && o !== null && typeof o.id === "string",
  );
}

/** The state without the browser-side order, which does not change what the API returns. */
function fetched(state: BsState): BsState {
  return { ...state, localSort: null };
}

export const bsKeys = {
  all: ["beatsaver"] as const,
  search: (state: BsState) => ["beatsaver", "search", fetched(state)] as const,
  playlists: (state: PlState) => ["beatsaver", "playlists", plFetched(state)] as const,
  playlist: (id: string, state: BsState) => ["beatsaver", "playlist", id, fetched(state)] as const,
  presets: ["beatsaver", "presets"] as const,
  config: ["beatsaver", "config"] as const,
};

const nextCursor = (last: { cursor: string | null }) => last.cursor ?? undefined;

export function useBsSearch(state: BsState) {
  return useInfiniteQuery({
    queryKey: bsKeys.search(state),
    queryFn: ({ pageParam, signal }) => searchMaps(state, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: nextCursor,
    retry,
  });
}

export function useBsPlaylistMaps(id: string, state: BsState) {
  return useInfiniteQuery({
    queryKey: bsKeys.playlist(id, state),
    queryFn: ({ pageParam, signal }) => getPlaylistMaps(id, state, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: nextCursor,
    retry,
  });
}

export function useBsPlaylists(state: PlState) {
  return useInfiniteQuery({
    queryKey: bsKeys.playlists(state),
    queryFn: ({ pageParam, signal }) => searchPlaylists(state, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: nextCursor,
    retry,
  });
}

export function usePresets() {
  return useQuery({
    queryKey: bsKeys.presets,
    queryFn: ({ signal }) => listPresets(signal),
    retry,
  });
}

export function useBsConfig() {
  return useQuery({
    queryKey: bsKeys.config,
    queryFn: ({ signal }) => getBsConfig(signal),
    retry,
    staleTime: Infinity,
  });
}

/** After a download job: refresh the installed flags here and the library list. */
export function refreshAfterDownload(client: QueryClient): void {
  void client.invalidateQueries({ queryKey: bsKeys.all });
  void client.invalidateQueries({ queryKey: ["maps"] });
}
