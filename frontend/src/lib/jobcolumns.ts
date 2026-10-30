/** Column set of the Jobs table; widths, resizing and storage code is the library's. */
import type { ColumnKey, ColumnSet } from "./columns";
import { defineColumns } from "./columnset";

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
const TRACKS: readonly ColumnKey[] = Object.values(JOB_COL);

export const JOB_COLUMNS: ColumnSet = defineColumns({
  tracks: TRACKS,
  // Each width holds the header label plus its filter and sort icons (Status also its tag); Title takes the rest.
  widths: { cover: 56, title: 200, length: 112, operation: 104, status: 150, actions: 96 },
  tier: { compact: { title: 100, length: 104, operation: 100, status: 140, actions: 64 } },
  storePrefix: "saber-tooth.columns.jobs.v4.",
  legacyPrefixes: [
    "saber-tooth.columns.jobs.v1.",
    "saber-tooth.columns.jobs.v2.",
    "saber-tooth.columns.jobs.v3.",
  ],
  fit: { operation: 100 },
  cells: { length: 104, status: 140, actions: 64 },
});
