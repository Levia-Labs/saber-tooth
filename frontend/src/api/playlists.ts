// Local playlists: the saved .bplist sources, built from library maps and job output.
import { useQuery } from "@tanstack/react-query";
import { request } from "./client";
import type { MapItem } from "./types";
import { retry } from "./queries";

export interface PlaylistSong {
  map_id: string | null;
  hash: string | null;
  key: string | null;
  song_name: string;
  mapper: string;
  /** No installed map matches the song's hash. */
  missing: boolean;
  cover_url?: string | null;
  /** The library item of an installed song; null when missing. */
  map?: MapItem | null;
}

export interface Playlist {
  id: string;
  title: string;
  author: string;
  description: string;
  /** Subfolder of the playlists folder the file is exported into. */
  folder: string;
  sync: boolean;
  sync_url: string;
  exported: string;
  updated_at: string;
  songs_count: number;
  missing_count: number;
  cover_url: string | null;
  songs?: PlaylistSong[];
}

export interface PlaylistConfig {
  export_enabled: boolean;
  live: Record<string, string>;
}

/** A song as sent to the server: a library map, or a hash-only BeatSaver entry. */
export interface SongInput {
  map_id?: string;
  hash?: string;
  key?: string;
  song_name?: string;
  mapper?: string;
}

export type CoverInput = { map_id: string } | { data: string } | { clear: true };

export type PlaylistInput = {
  title: string;
  author: string;
  description: string;
  folder: string;
  sync: boolean;
  songs: SongInput[];
  cover?: CoverInput;
};

export interface SongPick {
  map_id: string;
  song_name: string;
  mapper: string;
}

export const playlistKeys = {
  all: ["playlists"] as const,
  list: ["playlists", "list"] as const,
  one: (id: string) => ["playlists", "one", id] as const,
  config: ["playlists", "config"] as const,
};

const seg = encodeURIComponent;

export const listPlaylists = (signal?: AbortSignal) =>
  request<{ items: Playlist[] }>("GET", "/api/playlists", undefined, signal);
export const getPlaylist = (id: string) => request<Playlist>("GET", `/api/playlists/${seg(id)}`);
export const getPlaylistConfig = () => request<PlaylistConfig>("GET", "/api/playlists/config");
export const createPlaylist = (body: PlaylistInput) =>
  request<Playlist>("POST", "/api/playlists", body);
export const updatePlaylist = (id: string, body: PlaylistInput) =>
  request<Playlist>("POST", `/api/playlists/${seg(id)}`, body);
export const deletePlaylist = (id: string) =>
  request<unknown>("DELETE", `/api/playlists/${seg(id)}`);
export const exportPlaylist = (id: string, subfolder?: string) =>
  request<{ path: string; relative: string }>(
    "POST",
    `/api/playlists/${seg(id)}/export`,
    subfolder === undefined ? {} : { subfolder },
  );
export const jobPicks = (jobId: string) =>
  request<{ items: SongPick[] }>("GET", `/api/playlists/picks/jobs/${seg(jobId)}`);
export const livePicks = (name: string) =>
  request<{ items: SongPick[] }>("GET", `/api/playlists/picks/live/${seg(name)}`);

export function usePlaylists() {
  return useQuery({
    queryKey: playlistKeys.list,
    queryFn: ({ signal }) => listPlaylists(signal),
    retry,
  });
}

export function usePlaylist(id: string | null) {
  return useQuery({
    queryKey: playlistKeys.one(id ?? ""),
    queryFn: () => getPlaylist(id ?? ""),
    enabled: id !== null,
    retry,
  });
}

export function usePlaylistConfig() {
  return useQuery({ queryKey: playlistKeys.config, queryFn: getPlaylistConfig, retry });
}
