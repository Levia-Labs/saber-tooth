/** Pure helpers of the playlist page: the draft, its songs and the request body. */
import type { CoverInput, Playlist, PlaylistInput, PlaylistSong, SongPick } from "../api/playlists";
import type { MapItem } from "../api/types";

export interface Draft {
  title: string;
  author: string;
  description: string;
  folder: string;
  sync: boolean;
  songs: PlaylistSong[];
  /** What to send as the cover; undefined keeps the stored one. */
  cover: CoverInput | undefined;
  /** What the page shows as the cover now. */
  coverUrl: string | null;
}

export const EMPTY_DRAFT: Draft = {
  title: "",
  author: "",
  description: "",
  folder: "",
  sync: false,
  songs: [],
  cover: undefined,
  coverUrl: null,
};

export function draftOf(p: Playlist): Draft {
  return {
    title: p.title,
    author: p.author,
    description: p.description,
    folder: p.folder,
    sync: p.sync,
    songs: p.songs ?? [],
    cover: undefined,
    coverUrl: p.cover_url,
  };
}

/** The identity of a song inside a playlist. */
export const songId = (s: PlaylistSong): string => s.map_id ?? s.hash ?? "";

/** Songs picked from the library or a job's output; maps already in the draft are skipped. */
export function addPicks(
  songs: PlaylistSong[],
  picks: SongPick[],
  items: Readonly<Record<string, MapItem>>,
): PlaylistSong[] {
  const seen = new Set(songs.map(songId));
  const fresh: PlaylistSong[] = [];
  for (const p of picks) {
    if (seen.has(p.map_id)) continue;
    seen.add(p.map_id);
    fresh.push({
      map_id: p.map_id,
      hash: null,
      key: null,
      song_name: p.song_name,
      mapper: p.mapper,
      missing: false,
      cover_url: `/api/maps/${encodeURIComponent(p.map_id)}/cover`,
      map: items[p.map_id] ?? null,
    });
  }
  return [...songs, ...fresh];
}

export function toInput(d: Draft): PlaylistInput {
  const body: PlaylistInput = {
    title: d.title.trim(),
    author: d.author.trim(),
    description: d.description,
    folder: d.folder.trim(),
    sync: d.sync,
    songs: d.songs.map((s) =>
      s.map_id
        ? { map_id: s.map_id, song_name: s.song_name, mapper: s.mapper }
        : {
            hash: s.hash ?? undefined,
            key: s.key ?? undefined,
            song_name: s.song_name,
            mapper: s.mapper,
          },
    ),
  };
  if (d.cover) body.cover = d.cover;
  return body;
}

export const MAX_COVER_BYTES = 2 * 1024 * 1024;

/** Base64 of an uploaded image (no data: prefix), or an error text when it is not usable. */
export async function readCover(file: File): Promise<{ data: string; url: string } | string> {
  if (!/^image\/(png|jpeg)$/.test(file.type)) return "The cover must be a PNG or JPEG image.";
  if (file.size > MAX_COVER_BYTES) return "The cover must be under 2 MB.";
  const bytes = new Uint8Array(await file.arrayBuffer());
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  const data = btoa(bin);
  return { data, url: `data:${file.type};base64,${data}` };
}
