/** Column set of the Jobs table; widths, resizing and storage code is the library's. */
import type { ColumnKey, ColumnSet, Breakpoint } from "./columns";

const TRACKS: readonly ColumnKey[] = ["status", "actions", "title", "cover", "length"];

const DEFAULTS: Record<string, number> = {
  status: 190,
  actions: 130,
  title: 200,
  cover: 56,
  length: 170,
};

const same = (): Record<Breakpoint, Record<string, number>> => ({
  wide: { ...DEFAULTS },
  mid: { ...DEFAULTS },
  compact: { ...DEFAULTS, status: 170, length: 150 },
});

export const JOB_COLUMNS: ColumnSet = {
  tracks: { wide: TRACKS, mid: TRACKS, compact: TRACKS },
  defaults: same(),
  storePrefix: "saber-tooth.columns.jobs.v1.",
  legacyPrefixes: [],
};
