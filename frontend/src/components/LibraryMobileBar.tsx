import type { Facets, SortKey } from "../api/types";
import type { LibraryState } from "../lib/urlstate";
import { filterCounts, totalFilters } from "../lib/urlstate";
import { Icon } from "./icons";
import { MobileFilters } from "./MobileFilters";
import { Tip } from "./Tip";

/** Sortable columns offered below 1100px, where the table header is not usable. */
export const SORT_OPTIONS: [SortKey, string][] = [
  ["title", "Title"],
  ["mapper", "Author"],
  ["levels", "Levels"],
  ["environment", "Env"],
  ["status", "Status"],
  ["duration", "Length"],
  ["bpm", "BPM"],
];

interface Props {
  state: LibraryState;
  facets: Facets | undefined;
  update: (patch: Partial<LibraryState>, replace?: boolean) => void;
  clear: () => void;
}

/** Table controls above the list below 1100px: sort and direction, Filters and clear filters. */
export function LibraryMobileBar({ state, facets, update, clear }: Props) {
  const active = totalFilters(filterCounts(state)) > 0;
  const options = SORT_OPTIONS.some(([key]) => key === state.sort)
    ? SORT_OPTIONS
    : [...SORT_OPTIONS, [state.sort, state.sort] as [SortKey, string]];
  return (
    <div className="lib-mobile-bar">
      <div className="sort-group">
        <label className="sort-select">
          <span className="sr">Sort by</span>
          <select value={state.sort} onChange={(e) => update({ sort: e.target.value as SortKey })}>
            {options.map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="order-toggle"
          onClick={() => update({ order: state.order === "asc" ? "desc" : "asc" })}
        >
          <Icon name={state.order === "asc" ? "sort-asc" : "sort-desc"} />
          <span className="sr">{state.order === "asc" ? "Ascending" : "Descending"}</span>
        </button>
      </div>
      <div className="mobile-filters">
        <MobileFilters state={state} facets={facets} update={update} clear={clear} />
        {active && (
          <Tip text="Remove every filter.">
            <button type="button" className="btn icon tap" onClick={clear}>
              <Icon name="reject" />
              <span className="sr">Clear filters</span>
            </button>
          </Tip>
        )}
      </div>
    </div>
  );
}
