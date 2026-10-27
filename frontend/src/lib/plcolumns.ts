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
      maps: 76,
      rating: 84,
      upvotes: 88,
      length: 80,
      nps: 96,
      created: 104,
      actions: 140,
    },
    mid: {
      cover: 56,
      title: 120,
      author: 96,
      maps: 72,
      rating: 80,
      upvotes: 84,
      length: 76,
      created: 100,
      actions: 140,
    },
    compact: { cover: 56, title: 100, maps: 72, rating: 80, length: 76, actions: 140 },
  },
  storePrefix: "saber-tooth.columns.pl.v1.",
  legacyPrefixes: [],
};
