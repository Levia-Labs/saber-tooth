import { useCallback, useMemo, useRef } from "react";
import { SpecAlert } from "../components/Alert";
import { errorToAlert } from "../lib/alerts";
import { useFacets, useLibrary, useLiveRows } from "../api/queries";
import { useJobRunner } from "../api/jobs";
import { JobOutcome } from "../components/JobOutcome";
import { BarSlot, BarSlotProvider } from "../components/BarSlot";
import { SectionTabs } from "../components/SectionTabs";
import { LibraryTable } from "../components/LibraryTable";
import { LibraryMobileBar } from "../components/LibraryMobileBar";
import { LibraryTools } from "../components/LibraryTools";
import { useDocumentTitle, useLibraryState, useMediaQuery } from "../lib/hooks";
import { useColumns } from "../lib/useColumns";
import { filterCounts, totalFilters } from "../lib/urlstate";

export function LibraryPage() {
  useDocumentTitle("Library");
  const { state, update, clearFilters } = useLibraryState();
  const library = useLibrary(state);
  const facets = useFacets();
  const table = useRef<HTMLDivElement>(null);
  const columns = useColumns(table);
  const narrow = useMediaQuery("(max-width: 1099px)");
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
      <BarSlotProvider>
        <div className="lib-bar">
          <div className="lib-title">
            <SectionTabs active="library" heading="Library" headingId="library-heading" />
            <span className="count" aria-live="polite">
              {library.isPending ? "" : `${total} ${total === 1 ? "map" : "maps"}`}
            </span>
          </div>
          <BarSlot />
        </div>
        <LibraryTools learn={learn} onResetColumns={columns.api.resetAll} />
        <JobOutcome toastKey="Learn lightshows" job={learn.job} error={learn.error} />
        {narrow && (
          <LibraryMobileBar
            state={state}
            facets={facets.data}
            update={update}
            clear={clearFilters}
            matchCount={library.isPending ? undefined : total}
          />
        )}
        {library.isError && !library.data ? (
          <div className="lib-empty">
            <SpecAlert
              spec={errorToAlert(library.error, "Could not load the library")}
              onRetry={() => void library.refetch()}
            />
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
            table={table}
            columns={columns}
          />
        )}
      </BarSlotProvider>
    </section>
  );
}
