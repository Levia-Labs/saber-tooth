/** Column set of the BeatSaver list; the widths, resizing and storage code is the library's. */
import type { ColumnKey, ColumnSet } from "./columns";

export const BS_COLUMNS: ColumnSet = {
  tracks: {
    wide: [
      "select",
      "cover",
      "title",
      "author",
      "levels",
      "rating",
      "tempo",
      "tags",
      "status",
      "actions",
    ],
    mid: ["select", "cover", "title", "author", "levels", "rating", "tempo", "status", "actions"],
    compact: ["select", "cover", "title", "rating", "status", "actions"],
  },
  defaults: {
    wide: {
      select: 40,
      cover: 56,
      title: 200,
      author: 120,
      levels: 152,
      rating: 104,
      tempo: 104,
      tags: 180,
      status: 124,
      actions: 148,
    },
    mid: {
      select: 40,
      cover: 56,
      title: 200,
      author: 120,
      levels: 152,
      rating: 104,
      tempo: 104,
      status: 124,
      actions: 148,
    },
    compact: { select: 40, cover: 64, title: 100, rating: 96, status: 124, actions: 148 },
  },
  storePrefix: "saber-tooth.columns.bs.v1.",
  legacyPrefixes: [],
};

/** Cells every BeatSaver row renders, in order; `sub` is the compact subtitle. */
export const BS_ROW_CELLS: readonly (ColumnKey | "sub")[] = [
  "select",
  "cover",
  "title",
  "sub",
  "author",
  "levels",
  "rating",
  "tempo",
  "tags",
  "status",
  "actions",
];
