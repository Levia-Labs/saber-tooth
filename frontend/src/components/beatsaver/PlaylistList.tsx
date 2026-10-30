import { useListScroll } from "../../lib/listscroll";
import { EmptyState } from "../EmptyState";
import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { useCallback, useMemo, useRef, useState } from "react";
import {
  getPlaylistMaps,
  type BsMap,
  type BsPlaylist,
  type BsPlaylistPage,
} from "../../api/beatsaver";
import { DEFAULT_BS_STATE } from "../../lib/bsfilters";
import { errorToAlert } from "../../lib/alerts";
import { useMediaQuery } from "../../lib/hooks";
import { COMPACT_QUERY } from "../../lib/breakpoint";
import { PL_COLUMNS } from "../../lib/plcolumns";
import { isPlDefault, viewPlaylists } from "../../lib/plfilters";
import { PL_TIPS } from "../../lib/pltips";
import type { PlControls } from "../../lib/usePlState";
import { useColumns } from "../../lib/useColumns";
import { SpecAlert } from "../Alert";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import { useDownloads } from "./downloads";
import { DownloadSummary } from "./BsResults";
import { PlaylistTable } from "./PlaylistTable";
import { PlaylistToolbar } from "./PlaylistToolbar";
import { DownloadConfirm, MAX_BATCH } from "./SelectionBar";

const MAX_PAGES = 50;

type Query = UseInfiniteQueryResult<InfiniteData<BsPlaylistPage>, unknown>;

/** Every map of one playlist, following the cursor; stops at MAX_PAGES or a partial page. */
async function allMaps(id: string): Promise<BsMap[]> {
  const maps: BsMap[] = [];
  let cursor: string | null = null;
  for (let i = 0; i < MAX_PAGES; i++) {
    const page = await getPlaylistMaps(id, DEFAULT_BS_STATE, cursor);
    maps.push(...page.items);
    cursor = page.cursor;
    if (cursor === null || page.partial) break;
  }
  return maps;
}

/** Playlist search results as a table; header filters, infinite scroll and mobile cards. */
export function PlaylistList({ query, controls }: { query: Query; controls: PlControls }) {
  const { state, update, clearFilters } = controls;
  const table = useRef<HTMLDivElement>(null);
  const columns = useColumns(table, PL_COLUMNS);
  const narrow = useMediaQuery(COMPACT_QUERY);
  const downloads = useDownloads();
  const [fetching, setFetching] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [confirm, setConfirm] = useState<{ open: boolean; items: BsMap[] }>({
    open: false,
    items: [],
  });
  const { fetchNextPage, hasNextPage, isFetchingNextPage, isFetchNextPageError, refetch } = query;

  const pages = query.data?.pages;
  const items = useMemo(
    () => viewPlaylists(pages?.flatMap((p) => p.items) ?? [], state),
    [pages, state],
  );
  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  useListScroll(!query.isPending, items.length, hasNextPage, {
    load: loadMore,
    busy: isFetchingNextPage || isFetchNextPageError,
  });
  const retry = useCallback(
    () => void (hasNextPage ? fetchNextPage() : refetch()),
    [hasNextPage, fetchNextPage, refetch],
  );
  const downloadAll = useCallback(async (p: BsPlaylist) => {
    setFetching(true);
    setFailure(null);
    try {
      setConfirm({ open: true, items: await allMaps(p.id) });
    } catch (err) {
      setFailure(err);
    } finally {
      setFetching(false);
    }
  }, []);

  const filtered = !isPlDefault(state);
  const failedFirst = query.isError && !query.data;
  return (
    <>
      <PlaylistToolbar state={state} update={update} clear={clearFilters} narrow={narrow} />
      <DownloadSummary downloads={downloads} />
      {failure !== null && (
        <SpecAlert
          spec={errorToAlert(failure, "Could not load the playlist's maps")}
          onDismiss={() => setFailure(null)}
        />
      )}
      {failedFirst ? (
        <div className="lib-empty">
          <SpecAlert
            spec={errorToAlert(query.error, "Could not reach BeatSaver")}
            onRetry={retry}
          />
        </div>
      ) : (
        <>
          <PlaylistTable
            items={items}
            loading={query.isPending}
            hasNext={hasNextPage}
            fetchingNext={isFetchingNextPage}
            paused={isFetchNextPageError}
            onLoadMore={loadMore}
            state={state}
            update={update}
            busy={fetching || downloads.runner.busy}
            onDownloadAll={(p) => void downloadAll(p)}
            table={table}
            columns={columns}
            empty={
              <EmptyState
                icon={filtered ? "search" : "playlist"}
                text={filtered ? "No playlists match these filters." : "No playlists found."}
                action={
                  filtered ? (
                    <Tip text={PL_TIPS.clearFilters}>
                      <button type="button" className="btn plain" onClick={clearFilters}>
                        <Icon name="filter-x" />
                        <span className="label-hide-mobile">Clear filters</span>
                      </button>
                    </Tip>
                  ) : undefined
                }
              />
            }
          />
          {isFetchNextPageError && (
            <div className="lib-more">
              <SpecAlert
                spec={errorToAlert(query.error, "Could not load more playlists")}
                onRetry={retry}
              />
            </div>
          )}
        </>
      )}
      <DownloadConfirm
        items={confirm.items}
        open={confirm.open}
        onOpenChange={(open) => setConfirm((c) => ({ ...c, open }))}
        onConfirm={(ids) => void downloads.start(ids.slice(0, MAX_BATCH))}
      />
    </>
  );
}
