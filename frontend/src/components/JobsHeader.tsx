import type { ReactNode } from "react";
import type { JobKind, JobState, JobView } from "../api/types";
import type { ColumnKey } from "../lib/columns";
import { JOB_COL } from "../lib/jobcolumns";
import { KIND_LABEL, KIND_ORDER } from "../lib/jobkinds";
import { JOB_STATES, jobsFilterCount, type JobSort, type JobsState } from "../lib/jobfilters";
import type { ColumnsApi } from "../lib/useColumns";
import type { JobsPatch } from "../lib/useJobsState";
import { FilterPopover } from "./FilterPopover";
import { TextFilterBody } from "./TextFilterBody";
import { HeaderCell } from "./HeaderCell";
import { Icon } from "./icons";
import { JobsFilterBody } from "./JobsFilterBody";
import { Tip } from "./Tip";

const STATE_LABEL: Record<JobState, string> = {
  running: "Running",
  queued: "Queued",
  done: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

interface Props {
  state: JobsState;
  update: JobsPatch;
  columns: ColumnsApi;
  /** Every job before filtering, for the option counts. */
  jobs: JobView[];
}

interface CellProps extends Props {
  col: ColumnKey;
  label: string;
  sort?: JobSort;
  tip?: string;
  filter?: ReactNode;
}
function Cell({ col, label, columns, state, update, sort, tip, filter }: CellProps) {
  const sorted = sort !== undefined && state.sort === sort;
  const click = () =>
    sort &&
    update({ sort, ascending: sorted ? !state.ascending : sort === "status" || sort === "title" });
  const order = state.ascending ? "asc" : "desc";
  return (
    <HeaderCell
      col={col}
      label={label}
      columns={columns}
      prefix="jc"
      quiet={col === JOB_COL.icon}
      filter={filter}
      {...(sort && { onSort: click, tip: tip ?? `Sort by ${label}` })}
      order={sorted ? order : undefined}
    />
  );
}

const countBy = <T extends string>(jobs: JobView[], pick: (j: JobView) => T, value: T) =>
  jobs.filter((j) => pick(j) === value).length;

/** Sticky header row: sort toggles and Status, Kind and Title filters. */
export function JobsHeader(props: Props) {
  const { state, update, jobs } = props;
  const counts = jobsFilterCount(state);
  const clear = (column: string, n: number, patch: Partial<JobsState>) => ({
    column,
    disabled: n === 0,
    onClear: () => update(patch, true),
  });
  const cell = (col: ColumnKey) => ({ ...props, col, label: col });
  return (
    <div className="lib-head jobs-grid" role="row" aria-rowindex={1}>
      <Cell {...cell(JOB_COL.icon)} label="Icon" />
      <Cell
        {...cell(JOB_COL.title)}
        label="Title"
        sort="title"
        filter={
          <FilterPopover label="Title" tip="Filter by title" count={counts.title}>
            <TextFilterBody
              label="Title contains"
              placeholder="Title"
              q={state.q}
              onChange={(q, replace) => update({ q }, replace)}
              rowClear={clear("Title", counts.title, { q: "" })}
            />
          </FilterPopover>
        }
      />
      <Cell
        {...cell(JOB_COL.length)}
        label="Length"
        sort="length"
        tip="Sort by how long the job ran"
        filter={
          <Tip text="Sort by when the job was created">
            <button
              type="button"
              className={`filter-btn${state.sort === "created" ? " active" : ""}`}
              aria-label="Sort by created time"
              aria-pressed={state.sort === "created"}
              onClick={() =>
                update({
                  sort: "created",
                  ascending: state.sort === "created" ? !state.ascending : false,
                })
              }
            >
              <Icon name="clock" filled={state.sort === "created"} />
            </button>
          </Tip>
        }
      />
      <Cell
        {...cell(JOB_COL.operation)}
        label="Operation"
        filter={
          <div className="th-filters">
            <FilterPopover label="Kind" tip="Filter by kind of job" count={counts.kind}>
              <JobsFilterBody<JobKind>
                label="Kind"
                options={KIND_ORDER.map((value) => ({
                  value,
                  label: KIND_LABEL[value],
                  count: countBy(jobs, (j) => j.kind, value),
                }))}
                selected={state.kind}
                onChange={(kind) => update({ kind })}
                rowClear={clear("Kind", counts.kind, { kind: [] })}
              />
            </FilterPopover>
          </div>
        }
      />
      <Cell
        {...cell(JOB_COL.status)}
        label="Status"
        sort="status"
        tip="Running first, then queued, then finished. Click again to reverse."
        filter={
          <div className="th-filters">
            <FilterPopover label="Status" tip="Filter by status" count={counts.status}>
              <JobsFilterBody<JobState>
                label="Status"
                options={JOB_STATES.map((value) => ({
                  value,
                  label: STATE_LABEL[value],
                  count: countBy(jobs, (j) => j.status, value),
                }))}
                selected={state.status}
                onChange={(status) => update({ status })}
                rowClear={clear("Status", counts.status, { status: [] })}
              />
            </FilterPopover>
          </div>
        }
      />
      <Cell {...cell(JOB_COL.actions)} label="Actions" />
    </div>
  );
}
