/** Column set of the local playlists table; widths, resizing and storage code is the library's. */
import type { ColumnKey, ColumnSet } from "./columns";

/** Icon, Title, Songs, Folder, Sync and Actions reuse the library's cover, title, maps, env, status, actions keys. */
export const LP_COL = {
  icon: "cover",
  title: "title",
  songs: "maps",
  folder: "env",
  sync: "status",
  actions: "actions",
} as const satisfies Record<string, ColumnKey>;

const TRACKS: readonly ColumnKey[] = [
  LP_COL.icon,
  LP_COL.title,
  LP_COL.songs,
  LP_COL.folder,
  LP_COL.sync,
  LP_COL.actions,
];

/** Each width holds the header label plus its sort and filter icons; Title takes the rest. */
const DEFAULTS: Record<string, number> = {
  cover: 56,
  title: 200,
  maps: 124,
  env: 120,
  status: 110,
  actions: 132,
};

export const LP_COLUMNS: ColumnSet = {
  tracks: { wide: TRACKS, mid: TRACKS, compact: TRACKS },
  defaults: {
    wide: { ...DEFAULTS },
    mid: { ...DEFAULTS },
    compact: { ...DEFAULTS, title: 100, maps: 100, env: 90, status: 106, actions: 124 },
  },
  storePrefix: "saber-tooth.columns.lp.v1.",
  legacyPrefixes: [],
};
