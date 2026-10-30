/** Column set of the local playlists table; widths, resizing and storage code is the library's. */
import type { ColumnKey, ColumnSet } from "./columns";
import { defineColumns } from "./columnset";

/** Icon, Title, Songs, Folder, Sync and Actions reuse the library's cover, title, maps, env, status, actions keys. */
export const LP_COL = {
  icon: "cover",
  title: "title",
  songs: "maps",
  folder: "env",
  sync: "status",
  actions: "actions",
} as const satisfies Record<string, ColumnKey>;

export const LP_COLUMNS: ColumnSet = defineColumns({
  tracks: Object.values(LP_COL),
  // Each width holds the header label plus its sort and filter icons; Title takes the rest.
  widths: { cover: 56, title: 200, maps: 124, env: 120, status: 110, actions: 132 },
  tier: { compact: { title: 100, maps: 100, env: 90, status: 106, actions: 124 } },
  storePrefix: "saber-tooth.columns.lp.v1.",
  legacyPrefixes: [],
  cells: { maps: 100, actions: 124 },
});
