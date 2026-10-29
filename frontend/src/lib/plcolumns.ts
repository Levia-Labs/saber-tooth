/** Column set of the BeatSaver playlists list; widths, resizing and storage code is the library's. */
import type { ColumnSet } from "./columns";

export const PL_COLUMNS: ColumnSet = {
  tracks: {
    wide: [
      "cover",
      "title",
      "author",
      "maps",
      "rating",
      "upvotes",
      "length",
      "nps",
      "created",
      "actions",
    ],
    mid: ["cover", "title", "author", "maps", "rating", "upvotes", "length", "created", "actions"],
    compact: ["cover", "title", "maps", "rating", "length", "actions"],
  },
  defaults: {
    wide: {
      cover: 56,
      title: 160,
      author: 110,
      maps: 90,
      rating: 98,
      upvotes: 106,
      length: 102,
      nps: 72,
      created: 106,
      actions: 140,
    },
    mid: {
      cover: 56,
      title: 110,
      author: 96,
      maps: 90,
      rating: 98,
      upvotes: 106,
      length: 102,
      created: 106,
      actions: 140,
    },
    compact: { cover: 56, title: 100, maps: 90, rating: 98, length: 102, actions: 128 },
  },
  storePrefix: "saber-tooth.columns.pl.v2.",
  legacyPrefixes: ["saber-tooth.columns.pl.v1."],
  fit: { author: 78 },
};
