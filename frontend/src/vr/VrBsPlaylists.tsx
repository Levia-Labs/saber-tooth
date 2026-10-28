import { useCallback, useMemo } from "react";
import { Link } from "react-router";
import { useBsPlaylistMaps, useBsPlaylists } from "../api/beatsaver";
import type { Downloads } from "../components/beatsaver/downloads";
import { Cover } from "../components/Chips";
import { Icon } from "../components/icons";
import { SpecAlert } from "../components/Alert";
import { errorToAlert } from "../lib/alerts";
import { DEFAULT_BS_STATE } from "../lib/bsfilters";
import { formatDuration, plural } from "../lib/format";
import { DEFAULT_PL_STATE } from "../lib/plfilters";
import { MoreError } from "./MoreError";
import { useNearEnd } from "./useNearEnd";
import { VrBsList } from "./VrBsCard";

const PLAYLISTS = "/vr/beatsaver?view=playlists";

/** The playlist cards; Open leads to that playlist's maps. */
export function VrBsPlaylists() {
  const query = useBsPlaylists(DEFAULT_PL_STATE);
  const lists = useMemo(() => query.data?.pages.flatMap((p) => p.items) ?? [], [query.data]);
  const { fetchNextPage } = query;
  const more = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  const end = useNearEnd(
    more,
    Boolean(query.hasNextPage) && !query.isFetchingNextPage && !query.isFetchNextPageError,
  );
  return (
    <div className="vr-scroll">
      {query.isPending && (
        <p className="vr-help" role="status">
          Loading playlists
        </p>
      )}
      {query.isError && lists.length === 0 && (
        <SpecAlert
          spec={errorToAlert(query.error, "Could not load playlists")}
          onRetry={() => void query.refetch()}
        />
      )}
      <div className="vr-grid">
        {lists.map((p) => (
          <article key={p.id} className="vr-card" data-playlist={p.id}>
            <Cover url={p.cover_url} big />
            <div className="vr-card-body">
              <h2 className="vr-card-title">{p.name}</h2>
              <p className="vr-help">{p.owner}</p>
              <div className="vr-card-meta">
                <span>{plural(p.map_count, "map")}</span>
                <span>{formatDuration(p.duration)}</span>
              </div>
              <div className="vr-actions">
                <Link
                  className="btn accent vr-big"
                  aria-label={`Open ${p.name}`}
                  to={`${PLAYLISTS}&playlist=${encodeURIComponent(p.id)}`}
                >
                  Open
                </Link>
              </div>
            </div>
          </article>
        ))}
      </div>
      <div ref={end} aria-hidden="true" />
      {query.isFetchNextPageError && !query.isFetchingNextPage && <MoreError onRetry={more} />}
    </div>
  );
}

/** One playlist's maps with the same cards and Download as the maps view. */
export function VrBsPlaylistMaps({ id, downloads }: { id: string; downloads: Downloads }) {
  const query = useBsPlaylistMaps(id, DEFAULT_BS_STATE);
  const maps = useMemo(() => query.data?.pages.flatMap((p) => p.items) ?? [], [query.data]);
  const { fetchNextPage } = query;
  const more = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  return (
    <>
      <Link className="btn plain vr-back" to={PLAYLISTS}>
        <Icon name="back" />
        Playlists
      </Link>
      <h2 className="vr-heading">{query.data?.pages[0]?.playlist.name ?? "Playlist"}</h2>
      <VrBsList
        maps={maps}
        pending={query.isPending}
        error={query.error}
        onRetry={() => void query.refetch()}
        hasNext={query.hasNextPage}
        fetching={query.isFetchingNextPage}
        moreFailed={query.isFetchNextPageError}
        onMore={more}
        downloads={downloads}
        emptyText="This playlist has no maps."
      />
    </>
  );
}
