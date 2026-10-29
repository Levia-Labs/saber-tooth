import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router";
import {
  useBsPlaylistMaps,
  useBsPlaylists,
  type BsMap,
  type BsPlaylistMaps,
} from "../api/beatsaver";
import { BsResults } from "../components/beatsaver/BsResults";
import { BarSlotProvider } from "../components/BarSlot";
import { BsTabs } from "../components/beatsaver/BsTabs";
import type { Downloads } from "../components/beatsaver/downloads";
import { PlaylistList } from "../components/beatsaver/PlaylistList";
import { DownloadConfirm, MAX_BATCH } from "../components/beatsaver/SelectionBar";
import { Icon } from "../components/icons";
import { Tip } from "../components/Tip";
import { BS_TIPS } from "../lib/bstips";
import { useDocumentTitle } from "../lib/hooks";
import { useBsState } from "../lib/useBsState";
import { usePlState } from "../lib/usePlState";

const MAX_PAGES = 50;
type Query = UseInfiniteQueryResult<InfiniteData<BsPlaylistMaps>, unknown>;

function DownloadAll({ query, downloads }: { query: Query; downloads: Downloads }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<BsMap[]>([]);

  const begin = async () => {
    setLoading(true);
    let data = query.data;
    for (let i = 0; i < MAX_PAGES && data && (data.pages.at(-1)?.cursor ?? null) !== null; i++) {
      const next = await query.fetchNextPage();
      data = next.data;
      if (next.isError || (data?.pages.at(-1)?.partial ?? false)) break;
    }
    setItems(data?.pages.flatMap((p) => p.items) ?? []);
    setLoading(false);
    setOpen(true);
  };

  return (
    <>
      <Tip text={BS_TIPS.downloadAll}>
        <button
          type="button"
          className="btn primary"
          disabled={loading || downloads.runner.busy}
          onClick={() => void begin()}
        >
          <Icon name="download" />
          <span className="label-hide-mobile">
            {loading ? "Loading matches" : "Download all matching"}
          </span>
        </button>
      </Tip>
      <DownloadConfirm
        items={items}
        open={open}
        onOpenChange={setOpen}
        onConfirm={(ids) => void downloads.start(ids.slice(0, MAX_BATCH))}
      />
    </>
  );
}

function PlaylistDetail({ id }: { id: string }) {
  const controls = useBsState();
  const query = useBsPlaylistMaps(id, controls.state);
  const playlist = query.data?.pages[0]?.playlist;
  const name = playlist?.name ?? "Playlist";
  useDocumentTitle(name);
  return (
    <section className="library" aria-labelledby="bs-heading">
      <BarSlotProvider>
        <BsTabs
          heading={name}
          headingId="bs-heading"
          tab="playlists"
          note={playlist ? `${name} - ${playlist.owner}` : undefined}
        />
        <BsResults
          query={query}
          controls={controls}
          extra={({ downloads }) => (
            <div className="bs-playlist-actions">
              <Link className="btn plain" to="/beatsaver/playlists">
                <Icon name="back" />
                <span className="label-hide-mobile">All playlists</span>
              </Link>
              <DownloadAll query={query} downloads={downloads} />
            </div>
          )}
        />
      </BarSlotProvider>
    </section>
  );
}

function PlaylistSearch() {
  useDocumentTitle("BeatSaver playlists");
  const controls = usePlState();
  const query = useBsPlaylists(controls.state);
  return (
    <section className="library" aria-labelledby="bs-heading">
      <BarSlotProvider>
        <BsTabs heading="BeatSaver playlists" headingId="bs-heading" tab="playlists" />
        <PlaylistList query={query} controls={controls} />
      </BarSlotProvider>
    </section>
  );
}

export function BeatSaverPlaylistsPage() {
  const { id } = useParams();
  return id ? <PlaylistDetail key={id} id={id} /> : <PlaylistSearch />;
}
