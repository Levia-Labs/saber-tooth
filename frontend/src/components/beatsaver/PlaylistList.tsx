import { EmptyState } from "../EmptyState";
import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import {
  getPlaylistMaps,
  type BsMap,
  type BsPlaylist,
  type BsPlaylistPage,
} from "../../api/beatsaver";
import { DEFAULT_BS_STATE } from "../../lib/bsfilters";
import { errorToAlert } from "../../lib/alerts";
import { PL_COLUMNS } from "../../lib/plcolumns";
import { isPlDefault, viewPlaylists } from "../../lib/plfilters";
import { PL_TIPS } from "../../lib/pltips";
import type { PlControls } from "../../lib/usePlState";
import { SpecAlert } from "../Alert";
import { ListError } from "../ListError";
import { useInfiniteList } from "../../lib/useInfiniteList";
import { Icon } from "../icons";
import { Tip } from "../Tip";

import { DownloadSummary } from "./DownloadSummary";
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
  const [fetching, setFetching] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [confirm, setConfirm] = useState<{ open: boolean; items: BsMap[] }>({
    open: false,
    items: [],
  });
  const select = useCallback((all: BsPlaylist[]) => viewPlaylists(all, state), [state]);
  const list = useInfiniteList(query, PL_COLUMNS, select);
  const { items, downloads } = list;
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
  return (
    <>
      <PlaylistToolbar state={state} update={update} clear={clearFilters} narrow={list.narrow} />
      <DownloadSummary downloads={downloads} />
      {failure !== null && (
        <SpecAlert
          spec={errorToAlert(failure, "Could not load the playlist's maps")}
          onDismiss={() => setFailure(null)}
        />
      )}
      {list.failedFirst ? (
        <ListError
          alert
          scope="first"
          what="Could not reach BeatSaver"
          error={query.error}
          onRetry={list.retry}
        />
      ) : (
        <>
          <PlaylistTable
            items={items}
            loading={query.isPending}
            hasNext={query.hasNextPage}
            fetchingNext={query.isFetchingNextPage}
            paused={list.paused}
            onLoadMore={list.loadMore}
            state={state}
            update={update}
            busy={fetching || downloads.runner.busy}
            onDownloadAll={(p) => void downloadAll(p)}
            table={list.table}
            columns={list.columns}
            empty={
              <EmptyState
                icon={filtered ? "search" : "playlist"}
                text={filtered ? "No playlists match these filters." : "No playlists found."}
                action={
                  filtered ? (
                    <Tip text={PL_TIPS.clearFilters}>
                      <button type="button" className="btn plain" onClick={clearFilters}>
                        <Icon name="filter-x" />
                        <span className="label-collapsible">Clear filters</span>
                      </button>
                    </Tip>
                  ) : undefined
                }
              />
            }
          />
          {query.isFetchNextPageError && (
            <ListError
              alert
              scope="more"
              what="Could not load more playlists"
              error={query.error}
              onRetry={list.retry}
            />
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
