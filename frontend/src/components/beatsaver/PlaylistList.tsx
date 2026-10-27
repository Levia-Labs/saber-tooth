import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { Link } from "react-router";
import type { BsPlaylist, BsPlaylistPage } from "../../api/beatsaver";
import { errorMessage } from "../../api/client";
import { BS_TIPS } from "../../lib/bstips";
import { plural } from "../../lib/format";
import { Cover } from "../Chips";
import { Icon } from "../icons";
import { Tip } from "../Tip";

type Query = UseInfiniteQueryResult<InfiniteData<BsPlaylistPage>, unknown>;

function Row({ playlist }: { playlist: BsPlaylist }) {
  const to = `/beatsaver/playlists/${encodeURIComponent(playlist.id)}`;
  return (
    <li className="playlist-row">
      <Cover url={playlist.cover_url} />
      <div className="playlist-main">
        <Tip text={BS_TIPS.playlistOpen}>
          <Link className="title-link" to={to}>
            <Icon name="playlist" />
            <span>{playlist.name}</span>
          </Link>
        </Tip>
        <span className="sub">
          {playlist.owner} &middot; {plural(playlist.map_count, "map")}
          {playlist.curated ? " · Curated" : ""}
        </span>
      </div>
    </li>
  );
}

/** Playlist search results; the list scrolls inside the page shell like the maps table. */
export function PlaylistList({ query }: { query: Query }) {
  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  if (query.isPending) return <p className="muted">Loading playlists</p>;
  if (query.isError && !query.data) {
    return (
      <div className="lib-empty">
        <p className="err">Could not reach BeatSaver: {errorMessage(query.error)}</p>
        <button type="button" className="btn plain" onClick={() => void query.refetch()}>
          <Icon name="reset" />
          <span className="label-hide-mobile">Try again</span>
        </button>
      </div>
    );
  }
  return (
    <div className="lib-scroll">
      {items.length === 0 ? (
        <div className="lib-empty">
          <p>No playlists found.</p>
        </div>
      ) : (
        <ul className="playlist-list" aria-label="Playlists">
          {items.map((p) => (
            <Row key={p.id} playlist={p} />
          ))}
        </ul>
      )}
      {query.hasNextPage && (
        <div className="lib-more">
          {query.isFetchNextPageError && (
            <p className="err">Could not load more: {errorMessage(query.error)}</p>
          )}
          <button
            type="button"
            className="btn plain"
            disabled={query.isFetchingNextPage}
            onClick={() => void query.fetchNextPage()}
          >
            <Icon name="expand" />
            <span className="label-hide-mobile">Load more playlists</span>
          </button>
        </div>
      )}
    </div>
  );
}
