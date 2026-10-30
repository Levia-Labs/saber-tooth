import { LIBRARY_COLUMNS, type ColumnKey, type ColumnSet } from "./columns";

/**
 * Width each column header needs at 16 px so its label and its sort and filter buttons show in
 * full, measured in a browser plus 2 px. A column default below it truncates the label, so the
 * tracks per tier are chosen to fit with these widths (tests/columnfit.test.ts).
 */
export const HEADER_FIT: Partial<Record<ColumnKey, number>> = {
  select: 28,
  cover: 37,
  title: 91,
  author: 78,
  levels: 102,
  length: 102,
  bpm: 88,
  env: 84,
  status: 106,
  actions: 56,
  rating: 98,
  upvotes: 106,
  maps: 90,
  nps: 64,
  created: 106,
};

/** The narrow columns, sized to their content at the compact tier; Title takes the rest. */
export const NARROW_KEYS: readonly ColumnKey[] = [
  "length",
  "bpm",
  "status",
  "actions",
  "rating",
  "upvotes",
  "maps",
  "operation",
];

/** The least a narrow column needs: the wider of its header and its widest cell, in desktop px. */
export function contentMin(key: ColumnKey, set: ColumnSet = LIBRARY_COLUMNS): number {
  return Math.max(headerFit(key, set), set.cells?.[key] ?? 0);
}

/** The header width a column needs in a list, in desktop px. */
export function headerFit(key: ColumnKey, set: ColumnSet = LIBRARY_COLUMNS): number {
  return set.fit?.[key] ?? HEADER_FIT[key] ?? 0;
}
