import { EmptyState } from "../EmptyState";
import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { useCallback, type ReactNode } from "react";
import { useBsConfig, type BsMap, type BsPage } from "../../api/beatsaver";
import { BS_COLUMNS } from "../../lib/bscolumns";
import { BS_TIPS } from "../../lib/bstips";
import { isBsDefault } from "../../lib/bsfilters";
import { sortLoaded } from "../../lib/bsrating";
import { useInfiniteList } from "../../lib/useInfiniteList";
import type { BsControls } from "../../lib/useBsState";
import { Icon } from "../icons";
import { ListError } from "../ListError";
import { Tip } from "../Tip";
import { BsTable } from "./BsTable";
import { BsToolbar } from "./BsToolbar";
import { DownloadSummary } from "./DownloadSummary";
import { type Downloads } from "./downloads";
import { SelectionBar } from "./SelectionBar";
import { useSelection, type Selection } from "./selection";

type Query = UseInfiniteQueryResult<InfiniteData<BsPage>, unknown>;

interface Props {
  query: Query;
  controls: BsControls;
  /** Rendered between the toolbar and the list, e.g. the playlist's "Download all matching". */
  extra?: (ctx: { items: BsMap[]; downloads: Downloads; selection: Selection }) => ReactNode;
}

/** Toolbar, selection, banners, the list and the scan footer; shared by maps and playlists. */
export function BsResults({ query, controls, extra }: Props) {
  const { state, update, set, clearFilters } = controls;
  const config = useBsConfig();
  const selection = useSelection();
  const { order, ascending, localSort } = state;
  const select = useCallback(
    (all: BsMap[]) => sortLoaded(all, order, localSort, ascending),
    [order, localSort, ascending],
  );
  const list = useInfiniteList(query, BS_COLUMNS, select);
  const { items, downloads, lastPage, limited, retry } = list;
  const download = useCallback((id: string) => void downloads.start([id]), [downloads]);
  const selectAll = useCallback(() => selection.toggleAll(items), [selection, items]);

  const filtered = !isBsDefault(state);
  return (
    <>
      <BsToolbar
        state={state}
        update={update}
        set={set}
        clear={clearFilters}
        narrow={list.narrow}
      />
      {extra?.({ items, downloads, selection })}
      <DownloadSummary downloads={downloads} />
      <SelectionBar
        selection={selection}
        downloads={downloads}
        playlistsEnabled={config.data?.playlists_enabled ?? false}
      />
      {list.failedFirst ? (
        <ListError
          scope="first"
          what="Could not reach BeatSaver"
          error={query.error}
          onRetry={retry}
        />
      ) : (
        <>
          {limited && (
            <div className="result bs-banner" role="alert">
              <p>
                BeatSaver is limiting requests, so this list is partial.
                {lastPage?.retry_after ? ` Try again in ${lastPage.retry_after} seconds.` : ""}
              </p>
              <Tip text={BS_TIPS.retry}>
                <button type="button" className="btn plain" onClick={retry}>
                  <Icon name="reset" />
                  <span className="label-collapsible">Retry</span>
                </button>
              </Tip>
            </div>
          )}
          <BsTable
            items={items}
            loading={query.isPending}
            hasNext={query.hasNextPage}
            fetchingNext={query.isFetchingNextPage}
            paused={list.paused}
            onLoadMore={list.loadMore}
            state={state}
            update={update}
            selected={selection.ids}
            status={downloads.status}
            onSelect={selection.toggle}
            onSelectAll={selectAll}
            onDownload={download}
            table={list.table}
            columns={list.columns}
            empty={
              <EmptyState
                icon={filtered ? "search" : "maps"}
                text={filtered ? "No BeatSaver maps match these filters." : "No maps found."}
                action={
                  filtered ? (
                    <button type="button" className="btn plain" onClick={clearFilters}>
                      <Icon name="filter-x" />
                      <span className="label-collapsible">Clear filters</span>
                    </button>
                  ) : undefined
                }
              />
            }
          />
          {query.isFetchNextPageError && (
            <ListError
              scope="more"
              what="Could not load more maps"
              error={query.error}
              onRetry={retry}
            />
          )}
        </>
      )}
    </>
  );
}
