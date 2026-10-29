/** Column set of the Jobs table; widths, resizing and storage code is the library's. */
import type { ColumnKey, ColumnSet, Breakpoint } from "./columns";

export const JOB_COL = {
  icon: "cover",
  title: "title",
  length: "length",
  operation: "operation",
  status: "status",
  queue: "queue",
  rounds: "rounds",
  actions: "actions",
} as const satisfies Record<string, ColumnKey>;

/** Grid order: the library's Image, Title, Length, then the job columns. */
const TRACKS: readonly ColumnKey[] = [
  JOB_COL.icon,
  JOB_COL.title,
  JOB_COL.length,
  JOB_COL.operation,
  JOB_COL.status,
  JOB_COL.queue,
  JOB_COL.rounds,
  JOB_COL.actions,
];

/** Each width holds the header label plus its filter and sort icons; Title takes the rest. */
const DEFAULTS: Record<string, number> = {
  cover: 56,
  title: 200,
  length: 112,
  operation: 104,
  status: 104,
  queue: 72,
  rounds: 64,
  actions: 72,
};

const same = (): Record<Breakpoint, Record<string, number>> => ({
  wide: { ...DEFAULTS },
  mid: { ...DEFAULTS },
  compact: { ...DEFAULTS },
});

export const JOB_COLUMNS: ColumnSet = {
  tracks: { wide: TRACKS, mid: TRACKS, compact: TRACKS },
  defaults: same(),
  storePrefix: "saber-tooth.columns.jobs.v2.",
  legacyPrefixes: ["saber-tooth.columns.jobs.v1."],
};
