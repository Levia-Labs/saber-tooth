/** The playlist's songs as library rows: the library's filter state applied locally. */
import type { PlaylistSong } from "../api/playlists";
import { LEVEL_KEYS, STATUS_KEYS, type Facets, type MapItem } from "../api/types";
import { DEFAULT_STATE, totalFilters, filterCounts, type LibraryState } from "./urlstate";

export interface SongRow {
  /** Library item (a synthetic one for a missing song, which is `missing`). */
  item: MapItem;
  song: PlaylistSong;
  missing: boolean;
  /** Position in the playlist, the stable key of the row. */
  key: string;
}

/** A placeholder item for a song no installed map matches. */
function missingItem(song: PlaylistSong, key: string): MapItem {
  return {
    id: `missing-${key}`,
    folder: "",
    title: song.song_name || song.hash || "Unknown song",
    mapper: song.mapper,
    environment: "",
    parse_error: null,
    errors: 0,
    warnings: 0,
    scanned_at: null,
    status: "unscanned",
    cover_url: null,
    difficulties: [],
    approved: 0,
    pending: 0,
    bpm: null,
    duration_s: null,
    job: null,
  };
}

export function rowsOf(songs: readonly PlaylistSong[]): SongRow[] {
  return songs.map((song, i) => {
    const key = song.map_id ?? song.hash ?? String(i);
    const mapped = song.map && !song.missing ? song.map : null;
    return { item: mapped ?? missingItem(song, key), song, missing: !mapped, key };
  });
}

const rank = (item: MapItem) => {
  const idx = item.difficulties.map((d) => LEVEL_KEYS.indexOf(d as (typeof LEVEL_KEYS)[number]));
  return Math.max(-1, ...idx) * 8 + item.difficulties.length;
};

const text = (a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: "base" });

function compare(state: LibraryState, a: MapItem, b: MapItem): number {
  const num = (x: number | null, y: number | null) => (x ?? -1) - (y ?? -1);
  switch (state.sort) {
    case "mapper":
      return text(a.mapper, b.mapper);
    case "environment":
      return text(a.environment, b.environment);
    case "status":
      return STATUS_KEYS.indexOf(a.status) - STATUS_KEYS.indexOf(b.status);
    case "errors":
      return a.errors - b.errors;
    case "warnings":
      return a.warnings - b.warnings;
    case "scanned_at":
      return text(a.scanned_at ?? "", b.scanned_at ?? "");
    case "duration":
      return num(a.duration_s, b.duration_s);
    case "bpm":
      return num(a.bpm, b.bpm);
    case "levels":
      return rank(a) - rank(b);
    default:
      return text(a.title, b.title);
  }
}

function matches(s: LibraryState, item: MapItem): boolean {
  const q = s.q.trim().toLowerCase();
  if (q && !(s.qField === "mapper" ? item.mapper : item.title).toLowerCase().includes(q)) {
    return false;
  }
  if (s.status.length && !s.status.includes(item.status)) return false;
  if (s.env.length && !s.env.includes(item.environment)) return false;
  if (s.mapper.length && !s.mapper.includes(item.mapper)) return false;
  if (s.level.length) {
    const has = (l: string) => item.difficulties.includes(l);
    if (!(s.levelMode === "all" ? s.level.every(has) : s.level.some(has))) return false;
  }
  const within = (v: number | null, lo: number | null, hi: number | null) =>
    (lo === null && hi === null) ||
    (v !== null && (lo === null || v >= lo) && (hi === null || v <= hi));
  return (
    within(item.duration_s, s.durationMin, s.durationMax) && within(item.bpm, s.bpmMin, s.bpmMax)
  );
}

/** Rows after the library filters and sort; filters that need map data hide missing songs. */
export function applyState(rows: SongRow[], s: LibraryState): SongRow[] {
  const dir = s.order === "asc" ? 1 : -1;
  const onlyText = totalFilters(filterCounts({ ...s, q: "" })) === 0;
  return rows
    .filter((r) =>
      r.missing
        ? onlyText && matches({ ...DEFAULT_STATE, q: s.q, qField: s.qField }, r.item)
        : matches(s, r.item),
    )
    .sort((a, b) => dir * compare(s, a.item, b.item) || text(a.item.title, b.item.title));
}

/** What the filter popovers list: counts over the playlist's own songs. */
export function facetsOf(rows: SongRow[]): Facets {
  const found = rows.filter((r) => !r.missing).map((r) => r.item);
  const count = (values: string[]) =>
    [...values.reduce((m, v) => m.set(v, (m.get(v) ?? 0) + 1), new Map<string, number>())]
      .map(([name, n]) => ({ name, count: n }))
      .sort((a, b) => b.count - a.count || text(a.name, b.name));
  const range = (v: (number | null)[]) => {
    const n = v.filter((x): x is number => x !== null);
    return { min: n.length ? Math.min(...n) : null, max: n.length ? Math.max(...n) : null };
  };
  const status: Facets["status"] = {};
  for (const i of found) status[i.status] = (status[i.status] ?? 0) + 1;
  const levels = Object.fromEntries(
    LEVEL_KEYS.map((l) => [l, found.filter((i) => i.difficulties.includes(l)).length]),
  ) as Facets["levels"];
  return {
    status,
    environments: count(found.map((i) => i.environment).filter(Boolean)),
    mappers: count(found.map((i) => i.mapper).filter(Boolean)),
    levels,
    duration: range(found.map((i) => i.duration_s)),
    bpm: range(found.map((i) => i.bpm)),
    total: rows.length,
  };
}
