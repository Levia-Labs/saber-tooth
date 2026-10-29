/** Sort and filter of the local playlists table (client side: a playlists folder is small). */
import type { Playlist } from "../api/playlists";

export type LpSort = "title" | "songs" | "folder" | "sync";
export type LpSync = "any" | "on" | "off";

export interface LpState {
  q: string;
  sync: LpSync;
  missing: boolean;
  sort: LpSort;
  ascending: boolean;
}

export const LP_DEFAULT: LpState = {
  q: "",
  sync: "any",
  missing: false,
  sort: "title",
  ascending: true,
};

/** Filters in use per column, for the header badges. */
export function lpFilterCount(s: LpState): { title: number; sync: number; songs: number } {
  return { title: s.q.trim() ? 1 : 0, sync: s.sync === "any" ? 0 : 1, songs: s.missing ? 1 : 0 };
}

export const lpFiltered = (s: LpState): boolean =>
  Object.values(lpFilterCount(s)).some((n) => n > 0);

const text = (a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: "base" });

export function filterPlaylists(all: Playlist[], s: LpState): Playlist[] {
  const q = s.q.trim().toLowerCase();
  return all.filter(
    (p) =>
      (!q || `${p.title}\n${p.author}`.toLowerCase().includes(q)) &&
      (s.sync === "any" || p.sync === (s.sync === "on")) &&
      (!s.missing || p.missing_count > 0),
  );
}

export function sortPlaylists(rows: Playlist[], s: LpState): Playlist[] {
  const key = (a: Playlist, b: Playlist): number => {
    switch (s.sort) {
      case "songs":
        return a.songs_count - b.songs_count;
      case "folder":
        return text(a.folder, b.folder);
      case "sync":
        return Number(a.sync) - Number(b.sync);
      default:
        return text(a.title, b.title);
    }
  };
  const dir = s.ascending ? 1 : -1;
  return [...rows].sort(
    (a, b) => dir * key(a, b) || text(a.title, b.title) || a.id.localeCompare(b.id),
  );
}

/** Slug-safe preview of the file the export writes: Playlists/<folder>/<title>.bplist. */
export const exportHint = (folder: string): string =>
  `Playlists/${folder.trim() ? `${folder.trim().replace(/^\/+|\/+$/g, "")}/` : ""}`;

/** Shown wherever a file is written: the game reads playlists only when it loads them. */
export const REFRESH_HINT =
  "A playlist written while Beat Saber runs appears after PlaylistManager refreshes (Refresh Playlists in its menu) or after a game restart. With sync on, PlaylistManager refreshes it on its own.";
