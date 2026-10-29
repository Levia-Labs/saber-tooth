import type { ReactNode } from "react";
import type { JobKind, JobState, JobView } from "../api/types";
import type { ColumnKey } from "../lib/columns";
import { KIND_LABEL, KIND_ORDER } from "../lib/jobkinds";
import { JOB_STATES, jobsFilterCount, type JobSort, type JobsState } from "../lib/jobfilters";
import type { ColumnsApi } from "../lib/useColumns";
import type { JobsPatch } from "../lib/useJobsState";
import { FilterPopover } from "./FilterPopover";
import { TextFilterBody } from "./TextFilterBody";
import { Icon } from "./icons";
import { JobsFilterBody } from "./JobsFilterBody";
import { ResizeHandle } from "./ResizeHandle";
import { Tip } from "./Tip";
import { isResizable } from "../lib/columns";

const STATE_LABEL: Record<JobState, string> = {
  running: "Running",
  queued: "Queued",
  done: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

const HEADINGS: Partial<Record<ColumnKey, string>> = { cover: "Icon", length: "Length" };

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

function HeaderCell({ col, label, columns, state, update, sort, tip, filter }: CellProps) {
  const sorted = sort !== undefined && state.sort === sort;
  const aria = sorted ? (state.ascending ? "ascending" : "descending") : "none";
  const click = () => {
    if (!sort) return;
    update({ sort, ascending: sorted ? !state.ascending : sort === "status" || sort === "title" });
  };
  return (
    <div
      className={`th jc-${col}${col === "cover" ? " th-quiet" : ""}`}
      role="columnheader"
      aria-sort={sort ? aria : undefined}
    >
      <div className="th-row">
        {sort ? (
          <Tip text={tip ?? `Sort by ${label}`}>
            <button
              type="button"
              className="th-sort"
              onClick={click}
              aria-label={`Sort by ${label}`}
            >
              <span className="th-label">{label}</span>
            </button>
          </Tip>
        ) : (
          <span className="th-label">{label}</span>
        )}
        {filter}
        {sort && (
          <span className="th-slot" aria-hidden="true">
            {sorted && <Icon name={state.ascending ? "sort-asc" : "sort-desc"} />}
          </span>
        )}
      </div>
      {isResizable(col) && <ResizeHandle colKey={col} columns={columns} />}
    </div>
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
  const cell = (col: ColumnKey) => ({ ...props, col, label: HEADINGS[col] ?? col });
  return (
    <div className="lib-head jobs-grid" role="row" aria-rowindex={1}>
      <HeaderCell
        {...cell("status")}
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
      <HeaderCell {...cell("actions")} label="Actions" />
      <HeaderCell
        {...cell("title")}
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
      <HeaderCell {...cell("cover")} label="Icon" />
      <HeaderCell
        {...cell("length")}
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
    </div>
  );
}
