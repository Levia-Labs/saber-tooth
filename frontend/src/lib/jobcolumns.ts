/** Column set of the Jobs table; widths, resizing and storage code is the library's. */
import type { ColumnKey, ColumnSet } from "./columns";

/** Operation is a job-only key; the other columns reuse the library's. */
export const JOB_COL = {
  icon: "cover",
  title: "title",
  length: "length",
  operation: "operation",
  status: "status",
  actions: "actions",
} as const satisfies Record<string, ColumnKey>;

/** Grid order: the library's Image, Title, Length, then Operation, Status and Actions. */
const TRACKS: readonly ColumnKey[] = [
  JOB_COL.icon,
  JOB_COL.title,
  JOB_COL.length,
  JOB_COL.operation,
  JOB_COL.status,
  JOB_COL.actions,
];

/** Each width holds the header label plus its filter and sort icons (Status also its tag); Title takes the rest. */
const DEFAULTS: Record<string, number> = {
  cover: 56,
  title: 200,
  length: 112,
  operation: 104,
  status: 150,
  actions: 96,
};

export const JOB_COLUMNS: ColumnSet = {
  tracks: { wide: TRACKS, mid: TRACKS, compact: TRACKS },
  defaults: {
    wide: { ...DEFAULTS },
    mid: { ...DEFAULTS },
    compact: { ...DEFAULTS, title: 100, length: 104, operation: 100, status: 140, actions: 64 },
  },
  storePrefix: "saber-tooth.columns.jobs.v4.",
  legacyPrefixes: [
    "saber-tooth.columns.jobs.v1.",
    "saber-tooth.columns.jobs.v2.",
    "saber-tooth.columns.jobs.v3.",
  ],
  fit: { operation: 100 },
  cells: { length: 104, status: 140, actions: 64 },
};
