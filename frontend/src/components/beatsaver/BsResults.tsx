import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { useCallback, useMemo, useRef, type ReactNode } from "react";
import { useBsConfig, type BsMap, type BsPage } from "../../api/beatsaver";
import { errorMessage } from "../../api/client";
import { BS_COLUMNS } from "../../lib/bscolumns";
import { BS_TIPS } from "../../lib/bstips";
import { isBsDefault } from "../../lib/bsfilters";
import { plural } from "../../lib/format";
import { useMediaQuery } from "../../lib/hooks";
import { sortByUpvotes } from "../../lib/bsrating";
import { useColumns } from "../../lib/useColumns";
import type { BsControls } from "../../lib/useBsState";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import { BsTable } from "./BsTable";
import { BsToolbar } from "./BsToolbar";
import { useDownloads, tally, type Downloads } from "./downloads";
import { SelectionBar } from "./SelectionBar";
import { useSelection, type Selection } from "./selection";

type Query = UseInfiniteQueryResult<InfiniteData<BsPage>, unknown>;

interface Props {
  query: Query;
  controls: BsControls;
  /** Rendered between the toolbar and the list, e.g. the playlist's "Download all matching". */
  extra?: (ctx: { items: BsMap[]; downloads: Downloads; selection: Selection }) => ReactNode;
}

export function DownloadSummary({ downloads }: { downloads: Downloads }) {
  const { runner, results } = downloads;
  const t = tally(results);
  const failed = Object.values(results).filter((o) => o.status === "failed");
  if (runner.busy) {
    return (
      <div className="result" role="status">
        Downloading {plural(downloads.pending.size, "map")}
      </div>
    );
  }
  if (!runner.error && Object.keys(results).length === 0) return null;
  return (
    <div className="result" role="status">
      {runner.error && <p className="err">Download job failed: {runner.error}</p>}
      <p className={failed.length ? "" : "ok"}>
        Installed {t.installed}, skipped {t.skipped}, failed {t.failed}.
      </p>
      {failed.length > 0 && (
        <ul className="confirm-list">
          {failed.map((o) => (
            <li key={o.id}>
              {o.id}: {o.reason ?? "failed"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Toolbar, selection, banners, the list and the scan footer; shared by maps and playlists. */
export function BsResults({ query, controls, extra }: Props) {
  const { state, update, set, clearFilters } = controls;
  const table = useRef<HTMLDivElement>(null);
  const columns = useColumns(table, BS_COLUMNS);
  const narrow = useMediaQuery("(max-width: 1099px)");
  const config = useBsConfig();
  const downloads = useDownloads();
  const selection = useSelection();
  const { fetchNextPage, hasNextPage, isFetchingNextPage, isFetchNextPageError, refetch } = query;

  const pages = query.data?.pages;
  const order = state.order;
  const ascending = state.ascending;
  const items = useMemo(() => {
    const all = pages?.flatMap((p) => p.items) ?? [];
    return order === "Rating" ? sortByUpvotes(all, ascending) : all;
  }, [pages, order, ascending]);
  const scanned = pages?.reduce((n, p) => n + p.scanned, 0) ?? 0;
  const matched = pages?.reduce((n, p) => n + p.matched, 0) ?? 0;
  const lastPage = pages?.at(-1);
  const limited = Boolean(lastPage && (lastPage.partial || lastPage.retry_after));
  const paused = limited || isFetchNextPageError;

  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  const retry = useCallback(
    () => void (hasNextPage ? fetchNextPage() : refetch()),
    [hasNextPage, fetchNextPage, refetch],
  );
  const download = useCallback((id: string) => void downloads.start([id]), [downloads]);
  const selectAll = useCallback(() => selection.toggleAll(items), [selection, items]);

  const filtered = !isBsDefault(state);
  const failedFirst = query.isError && !query.data;
  return (
    <>
      <BsToolbar state={state} update={update} set={set} clear={clearFilters} narrow={narrow} />
      {extra?.({ items, downloads, selection })}
      <DownloadSummary downloads={downloads} />
      <SelectionBar
        selection={selection}
        downloads={downloads}
        playlistsEnabled={config.data?.playlists_enabled ?? false}
      />
      {failedFirst ? (
        <div className="lib-empty">
          <p className="err">Could not reach BeatSaver: {errorMessage(query.error)}</p>
          <Tip text={BS_TIPS.retry}>
            <button type="button" className="btn plain" onClick={retry}>
              <Icon name="reset" />
              <span className="label-hide-mobile">Try again</span>
            </button>
          </Tip>
        </div>
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
                  <span className="label-hide-mobile">Retry</span>
                </button>
              </Tip>
            </div>
          )}
          <BsTable
            items={items}
            loading={query.isPending}
            hasNext={hasNextPage}
            fetchingNext={isFetchingNextPage}
            paused={paused}
            onLoadMore={loadMore}
            state={state}
            update={update}
            selected={selection.ids}
            status={downloads.status}
            onSelect={selection.toggle}
            onSelectAll={selectAll}
            onDownload={download}
            table={table}
            columns={columns}
            empty={
              <div className="lib-empty">
                <p>{filtered ? "No BeatSaver maps match these filters." : "No maps found."}</p>
                {filtered && (
                  <button type="button" className="btn plain" onClick={clearFilters}>
                    <Icon name="filter-x" />
                    <span className="label-hide-mobile">Clear filters</span>
                  </button>
                )}
              </div>
            }
          />
          {isFetchNextPageError && (
            <div className="lib-more">
              <p className="err">Could not load more maps: {errorMessage(query.error)}</p>
              <button type="button" className="btn plain" onClick={retry}>
                <Icon name="expand" />
                <span className="label-hide-mobile">Load more</span>
              </button>
            </div>
          )}
          <p className="bs-footer count" aria-live="polite">
            {query.isPending ? "" : `Scanned ${scanned} BeatSaver maps, ${matched} match`}
          </p>
        </>
      )}
    </>
  );
}
