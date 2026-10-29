import type { ReactNode } from "react";
import type { Facets, SortKey } from "../api/types";
import { filterCounts, nextSort, RANGES, type LibraryState } from "../lib/urlstate";
import {
  EnvFilterBody,
  LevelsFilterBody,
  MapperListBody,
  StatusFilterBody,
  TextFilterBody,
} from "./FilterBodies";
import { FilterPopover } from "./FilterPopover";
import { Icon } from "./icons";
import { RangeFilterBody } from "./RangeFilterBody";
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
          </button>
        ) : (
          <span className="th-label">{label}</span>
        )}
        {filter}
        {sort && (
          <span className="th-slot" aria-hidden="true">
            {sorted && <Icon name={state.order === "asc" ? "sort-asc" : "sort-desc"} />}
          </span>
        )}
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
              placeholder="Title"
              q={state.qField === "title" ? state.q : ""}
              onChange={(q, replace) => update({ q, qField: "title" }, replace)}
              rowClear={{
                column: "Title",
                disabled: !counts.title,
                onClear: () => update({ q: "", qField: "title" }, true),
              }}
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
            <MapperListBody
              selected={state.mapper}
              facets={facets}
              onChange={(mapper) => update({ mapper })}
              rowClear={{
                column: "Author",
                disabled: !counts.author,
                onClear: () => update({ q: "", qField: "mapper", mapper: [] }),
              }}
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
              rowClear={{
                column: "Levels",
                disabled: !counts.levels,
                onClear: () => update({ level: [] }),
              }}
            />
          </FilterPopover>
        }
      />
      <HeaderCell
        col="length"
        sort="duration"
        {...cell}
        filter={
          <FilterPopover label="Length" tip="Filter by song length." count={counts.length}>
            <RangeFilterBody
              name="Length"
              kind="duration"
              min={state.durationMin}
              max={state.durationMax}
              bounds={facets?.duration}
              limit={RANGES.durationMax.max}
              onChange={(r, replace) =>
                update(
                  {
                    ...("min" in r && { durationMin: r.min }),
                    ...("max" in r && { durationMax: r.max }),
                  },
                  replace,
                )
              }
              rowClear={{
                column: "Length",
                disabled: !counts.length,
                onClear: () => update({ durationMin: null, durationMax: null }),
              }}
            />
          </FilterPopover>
        }
      />
      <HeaderCell
        col="bpm"
        sort="bpm"
        {...cell}
        filter={
          <FilterPopover label="BPM" tip="Filter by beats per minute." count={counts.bpm}>
            <RangeFilterBody
              name="BPM"
              kind="number"
              min={state.bpmMin}
              max={state.bpmMax}
              bounds={facets?.bpm}
              limit={RANGES.bpmMax.max}
              onChange={(r, replace) =>
                update(
                  {
                    ...("min" in r && { bpmMin: r.min }),
                    ...("max" in r && { bpmMax: r.max }),
                  },
                  replace,
                )
              }
              rowClear={{
                column: "BPM",
                disabled: !counts.bpm,
                onClear: () => update({ bpmMin: null, bpmMax: null }),
              }}
            />
          </FilterPopover>
        }
      />
      <HeaderCell
        col="env"
        sort="environment"
        {...cell}
        filter={
          <FilterPopover label="Env" tip="Filter by environment." count={counts.env}>
            <EnvFilterBody
              selected={state.env}
              facets={facets}
              onChange={(env) => update({ env })}
              rowClear={{
                column: "Env",
                disabled: !counts.env,
                onClear: () => update({ env: [] }),
              }}
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
              rowClear={{
                column: "Status",
                disabled: !counts.status,
                onClear: () => update({ status: [] }),
              }}
            />
          </FilterPopover>
        }
      />
      <HeaderCell col="actions" {...cell} />
    </div>
  );
}
