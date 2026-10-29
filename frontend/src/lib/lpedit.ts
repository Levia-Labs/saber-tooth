/** Pure helpers of the playlist editor: the draft, its songs and the request body. */
import type { CoverInput, SongPick, Playlist, PlaylistInput, PlaylistSong } from "../api/playlists";

export interface DraftSong {
  map_id: string | null;
  hash: string | null;
  key: string | null;
  song_name: string;
  mapper: string;
  missing: boolean;
  cover_url: string | null;
}

export interface Draft {
  title: string;
  author: string;
  description: string;
  folder: string;
  sync: boolean;
  songs: DraftSong[];
  /** What to send as the cover; undefined keeps the stored one. */
  cover: CoverInput | undefined;
  /** What the editor shows as the cover now. */
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

export const draftSong = (s: PlaylistSong): DraftSong => ({
  map_id: s.map_id,
  hash: s.hash,
  key: s.key,
  song_name: s.song_name,
  mapper: s.mapper,
  missing: s.missing,
  cover_url: s.cover_url ?? null,
});

export function draftOf(p: Playlist): Draft {
  return {
    title: p.title,
    author: p.author,
    description: p.description,
    folder: p.folder,
    sync: p.sync,
    songs: (p.songs ?? []).map(draftSong),
    cover: undefined,
    coverUrl: p.cover_url,
  };
}

/** Songs picked from the library or a job's output; maps already in the draft are skipped. */
export function addPicks(songs: DraftSong[], picks: SongPick[]): DraftSong[] {
  const have = new Set(songs.map((s) => s.map_id).filter(Boolean));
  const fresh = picks
    .filter((p) => !have.has(p.map_id))
    .map<DraftSong>((p) => ({
      map_id: p.map_id,
      hash: null,
      key: null,
      song_name: p.song_name,
      mapper: p.mapper,
      missing: false,
      cover_url: `/api/maps/${encodeURIComponent(p.map_id)}/cover`,
    }));
  const seen = new Set<string>();
  return [...songs, ...fresh].filter((s) => {
    const id = s.map_id ?? s.hash ?? "";
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
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

/** Base64 of an uploaded image (no data: prefix), or an error text when it is not usable. */
export async function readCover(file: File): Promise<{ data: string; url: string } | string> {
  if (!/^image\/(png|jpeg)$/.test(file.type)) return "The cover must be a PNG or JPEG image.";
  if (file.size > 2 * 1024 * 1024) return "The cover must be under 2 MB.";
  const bytes = new Uint8Array(await file.arrayBuffer());
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return { data: btoa(bin), url: `data:${file.type};base64,${btoa(bin)}` };
}
