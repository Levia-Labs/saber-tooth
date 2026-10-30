/** Column set of the BeatSaver list; the widths, resizing and storage code is the library's. */
import type { ColumnKey, ColumnSet } from "./columns";
import { defineColumns } from "./columnset";

export const BS_COLUMNS: ColumnSet = defineColumns({
  tracks: {
    wide: [
      "select",
      "cover",
      "title",
      "author",
      "levels",
      "rating",
      "upvotes",
      "length",
      "bpm",
      "tags",
      "status",
      "actions",
    ],
    mid: [
      "select",
      "cover",
      "title",
      "author",
      "levels",
      "rating",
      "upvotes",
      "length",
      "status",
      "actions",
    ],
    compact: ["select", "cover", "title", "rating", "upvotes", "status", "actions"],
  },
  // Sized so each breakpoint fits at its narrowest viewport (1280, 1100, 720) with no scroll.
  widths: {
    select: 36,
    cover: 56,
    title: 100,
    author: 90,
    levels: 140,
    rating: 98,
    upvotes: 106,
    length: 102,
    bpm: 88,
    tags: 84,
    status: 60,
    actions: 96,
  },
  tier: { mid: { select: 32, author: 80 }, compact: { select: 32 } },
  storePrefix: "saber-tooth.columns.bs.v3.",
  legacyPrefixes: ["saber-tooth.columns.bs.v1.", "saber-tooth.columns.bs.v2."],
  fit: { select: 28, author: 46, levels: 78, status: 50 },
  cells: { status: 60, actions: 96 },
});

/** Cells every BeatSaver row renders, in order; `sub` is the compact subtitle. */
export const BS_ROW_CELLS: readonly (ColumnKey | "sub")[] = [
  "select",
  "cover",
  "title",
  "sub",
  "author",
  "levels",
  "rating",
  "upvotes",
  "length",
  "bpm",
  "tags",
  "status",
  "actions",
];
