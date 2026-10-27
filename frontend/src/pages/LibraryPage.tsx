import { useCallback, useMemo } from "react";
import { errorMessage, learnLightshows } from "../api/client";
import { useFacets, useLibrary, useLiveRows } from "../api/queries";
import { useJobRunner } from "../api/jobs";
import type { SortKey } from "../api/types";
import { ActionButton, ActionLink } from "../components/Buttons";
import { JobOutcome } from "../components/JobOutcome";
import { LibraryTable } from "../components/LibraryTable";
import { MobileFilters } from "../components/MobileFilters";
import { useDocumentTitle, useLibraryState } from "../lib/hooks";
import { TIPS } from "../lib/tips";
import { filterCounts, totalFilters } from "../lib/urlstate";

const SORT_OPTIONS: [SortKey, string][] = [
  ["title", "Title"],
  ["mapper", "Author"],
  ["levels", "Levels"],
  ["environment", "Environment"],
  ["status", "Status"],
  ["errors", "Errors"],
  ["warnings", "Warnings"],
  ["scanned_at", "Last scanned"],
  ["duration", "Length"],
  ["bpm", "BPM"],
];

export function LibraryPage() {
  useDocumentTitle("Library");
  const { state, update, clearFilters } = useLibraryState();
  const library = useLibrary(state);
  const facets = useFacets();
  const learn = useJobRunner("Learn lightshows");
  const { fetchNextPage, hasNextPage, isFetchingNextPage, isFetchNextPageError } = library;

  const items = useMemo(() => library.data?.pages.flatMap((p) => p.items) ?? [], [library.data]);
  const total = library.data?.pages.at(-1)?.total ?? 0;
  useLiveRows(items);

  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  const counts = filterCounts(state);
  const filtered = totalFilters(counts) > 0;

  return (
    <section className="library" aria-labelledby="library-heading">
      <div className="lib-bar">
        <div className="lib-title">
          <h1 id="library-heading" tabIndex={-1} data-page-heading>
            Library
          </h1>
          <span className="count" aria-live="polite">
            {library.isPending ? "" : `${total} ${total === 1 ? "map" : "maps"}`}
          </span>
        </div>
        <div className="lib-tools">
          <label className="sort-select">
            <span className="sr">Sort by</span>
            <select
              value={state.sort}
              onChange={(e) => update({ sort: e.target.value as SortKey })}
            >
              {SORT_OPTIONS.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn plain order-toggle"
            onClick={() => update({ order: state.order === "asc" ? "desc" : "asc" })}
          >
            {state.order === "asc" ? "Ascending" : "Descending"}
          </button>
          <MobileFilters state={state} facets={facets.data} update={update} clear={clearFilters} />
          <ActionLink
            icon="generate"
            label="Generate map"
            tip={TIPS.generate}
            to="/new"
            text
            variant="primary"
          />
          <ActionButton
            icon="learn"
            label="Learn lightshows"
            tip={TIPS.learn}
            text
            disabled={learn.busy}
            onClick={() => void learn.run(learnLightshows)}
          />
        </div>
      </div>
      <JobOutcome job={learn.job} error={learn.error} />
      {library.isError && !library.data ? (
        <div className="lib-empty">
          <p className="err">Could not load the library: {errorMessage(library.error)}</p>
          <button type="button" className="btn plain" onClick={() => void library.refetch()}>
            Try again
          </button>
        </div>
      ) : (
        <LibraryTable
          items={items}
          total={total}
          loading={library.isPending}
          hasNext={hasNextPage}
          fetchingNext={isFetchingNextPage}
          nextFailed={isFetchNextPageError}
          onLoadMore={loadMore}
          state={state}
          facets={facets.data}
          update={update}
          onClear={clearFilters}
          filtered={filtered}
        />
      )}
    </section>
  );
}
