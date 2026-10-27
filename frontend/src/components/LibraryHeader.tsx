import type { ReactNode } from "react";
import type { Facets, SortKey } from "../api/types";
import { filterCounts, nextSort, type LibraryState } from "../lib/urlstate";
import { EnvFilterBody, StatusFilterBody, TitleFilterBody } from "./FilterBodies";
import { FilterPopover } from "./FilterPopover";
import { Icon } from "./icons";

interface Props {
  state: LibraryState;
  facets: Facets | undefined;
  update: (patch: Partial<LibraryState>, replace?: boolean) => void;
}

interface CellProps {
  label: string;
  sort?: SortKey;
  className: string;
  state: LibraryState;
  update: Props["update"];
  filter?: ReactNode;
}

function HeaderCell({ label, sort, className, state, update, filter }: CellProps) {
  const sorted = sort !== undefined && state.sort === sort;
  const aria = sorted ? (state.order === "asc" ? "ascending" : "descending") : "none";
  return (
    <div className={`th ${className}`} role="columnheader" aria-sort={sort ? aria : undefined}>
      {sort ? (
        <button
          type="button"
          className="th-sort"
          onClick={() => update(nextSort(state, sort))}
          aria-label={`Sort by ${label}`}
        >
          <span className="th-label">{label}</span>
          <span className="th-slot">
            {sorted && <Icon name={state.order === "asc" ? "sort-asc" : "sort-desc"} />}
          </span>
        </button>
      ) : (
        <span className="th-label">{label}</span>
      )}
      {filter}
    </div>
  );
}

/** Sticky column header row: sort buttons and the Title, Status and Environment filters. */
export function LibraryHeader({ state, facets, update }: Props) {
  const counts = filterCounts(state);
  const cell = { state, update };
  return (
    <div className="lib-head lib-grid" role="row" aria-rowindex={1}>
      <HeaderCell label="Image" className="col-cover sr" {...cell} />
      <HeaderCell
        label="Title"
        sort="title"
        className="col-title"
        {...cell}
        filter={
          <FilterPopover label="Title" tip="Filter by name or mapper." count={counts.title}>
            <TitleFilterBody q={state.q} onChange={(q, replace) => update({ q }, replace)} />
          </FilterPopover>
        }
      />
      <HeaderCell label="Levels" className="col-levels" {...cell} />
      <HeaderCell label="Length" sort="duration" className="col-length" {...cell} />
      <HeaderCell label="BPM" sort="bpm" className="col-bpm" {...cell} />
      <HeaderCell
        label="Environment"
        sort="environment"
        className="col-env"
        {...cell}
        filter={
          <FilterPopover label="Environment" tip="Filter by environment." count={counts.env}>
            <EnvFilterBody
              selected={state.env}
              facets={facets}
              onChange={(env) => update({ env })}
            />
          </FilterPopover>
        }
      />
      <HeaderCell
        label="Status"
        sort="status"
        className="col-status"
        {...cell}
        filter={
          <FilterPopover label="Status" tip="Filter by status." count={counts.status}>
            <StatusFilterBody
              selected={state.status}
              facets={facets}
              onChange={(status) => update({ status })}
            />
          </FilterPopover>
        }
      />
      <HeaderCell label="Actions" className="col-actions" {...cell} />
    </div>
  );
}
