import type { ReactNode } from "react";
import type { Facets, SortKey } from "../api/types";
import { filterCounts, nextSort, type LibraryState } from "../lib/urlstate";
import {
  EnvFilterBody,
  LevelsFilterBody,
  MapperListBody,
  StatusFilterBody,
  TextFilterBody,
} from "./FilterBodies";
import { FilterPopover } from "./FilterPopover";
import { Icon } from "./icons";
import { ResizeHandle } from "./ResizeHandle";
import { isResizable, LABELS, type ColumnKey } from "../lib/columns";
import type { ColumnsApi } from "../lib/useColumns";

interface Props {
  state: LibraryState;
  facets: Facets | undefined;
  update: (patch: Partial<LibraryState>, replace?: boolean) => void;
  columns: ColumnsApi;
}

interface CellProps {
  col: ColumnKey;
  columns: ColumnsApi;
  sort?: SortKey;
  state: LibraryState;
  update: Props["update"];
  filter?: ReactNode;
}

function HeaderCell({ col, columns, sort, state, update, filter }: CellProps) {
  const label = LABELS[col];
  const className = `col-${col}${col === "cover" ? " th-quiet" : ""}`;
  const sorted = sort !== undefined && state.sort === sort;
  const aria = sorted ? (state.order === "asc" ? "ascending" : "descending") : "none";
  return (
    <div className={`th ${className}`} role="columnheader" aria-sort={sort ? aria : undefined}>
      <div className="th-row">
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
      {isResizable(col) && <ResizeHandle colKey={col} columns={columns} />}
    </div>
  );
}

/** Sticky column header row: sort buttons and the Title, Status and Environment filters. */
export function LibraryHeader({ state, facets, update, columns }: Props) {
  const counts = filterCounts(state);
  const cell = { state, update, columns };
  return (
    <div className="lib-head lib-grid" role="row" aria-rowindex={1}>
      <HeaderCell col="cover" {...cell} />
      <HeaderCell
        col="title"
        sort="title"
        {...cell}
        filter={
          <FilterPopover label="Title" tip="Filter by title." count={counts.title}>
            <TextFilterBody
              label="Title contains"
              q={state.qField === "title" ? state.q : ""}
              onChange={(q, replace) => update({ q, qField: "title" }, replace)}
            />
          </FilterPopover>
        }
      />
      <HeaderCell
        col="author"
        sort="mapper"
        {...cell}
        filter={
          <FilterPopover label="Author" tip="Filter by mapper." count={counts.author}>
            <TextFilterBody
              label="Name contains"
              q={state.qField === "mapper" ? state.q : ""}
              onChange={(q, replace) => update({ q, qField: "mapper" }, replace)}
            />
            <MapperListBody
              selected={state.mapper}
              facets={facets}
              onChange={(mapper) => update({ mapper })}
            />
          </FilterPopover>
        }
      />
      <HeaderCell
        col="levels"
        sort="levels"
        {...cell}
        filter={
          <FilterPopover label="Levels" tip="Filter by difficulty level." count={counts.levels}>
            <LevelsFilterBody
              selected={state.level}
              mode={state.levelMode}
              facets={facets}
              onChange={(patch) => update(patch)}
            />
          </FilterPopover>
        }
      />
      <HeaderCell col="length" sort="duration" {...cell} />
      <HeaderCell col="bpm" sort="bpm" {...cell} />
      <HeaderCell
        col="env"
        sort="environment"
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
        col="status"
        sort="status"
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
      <HeaderCell col="actions" {...cell} />
    </div>
  );
}
