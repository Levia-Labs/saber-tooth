import { useRef, type ReactNode } from "react";
import type { JobView } from "../api/types";
import { JOB_COLUMNS } from "../lib/jobcolumns";
import type { JobsState } from "../lib/jobfilters";
import { useColumns } from "../lib/useColumns";
import type { JobsPatch } from "../lib/useJobsState";
import { JobsHeader } from "./JobsHeader";
import { JobsRow } from "./JobsRow";

interface Props {
  /** Filtered and sorted rows. */
  rows: JobView[];
  /** Every job, for the filter counts. */
  all: JobView[];
  state: JobsState;
  update: JobsPatch;
  now: number;
  onCancel: (job: JobView) => void;
  onRetry: (job: JobView) => void;
  retrying: ReadonlySet<string>;
  empty: ReactNode;
}

/** One table of every job: sort and filter in the header, one row per job. */
export function JobsTable({
  rows,
  all,
  state,
  update,
  now,
  onCancel,
  onRetry,
  retrying,
  empty,
}: Props) {
  const table = useRef<HTMLDivElement>(null);
  const columns = useColumns(table, JOB_COLUMNS);
  return (
    <div className="lib-scroll jobs-scroll" tabIndex={-1}>
      <div
        role="table"
        aria-label="Jobs"
        aria-rowcount={rows.length + 1}
        className="lib-table jobs-table"
        ref={table}
        style={columns.style}
      >
        <JobsHeader state={state} update={update} columns={columns.api} jobs={all} />
        <div role="rowgroup">
          {rows.map((job, i) => (
            <JobsRow
              key={job.id}
              job={job}
              index={i}
              now={now}
              onCancel={onCancel}
              onRetry={onRetry}
              retrying={retrying}
            />
          ))}
        </div>
      </div>
      {rows.length === 0 && empty}
    </div>
  );
}
