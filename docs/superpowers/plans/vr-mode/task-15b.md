# Task 15: VR BeatSaver screen (part b)

Continues [task-15a.md](task-15a.md).

- [ ] **Step 3: Implement the card and the list**

Create `frontend/src/vr/VrBsCard.tsx`:

```tsx
import type { BsMap } from "../api/beatsaver";
import { SpecAlert } from "../components/Alert";
import type { Downloads } from "../components/beatsaver/downloads";
import { Cover, LevelChips } from "../components/Chips";
import { PreviewButton } from "../components/PreviewButton";
import { errorToAlert } from "../lib/alerts";
import { formatCount, formatDuration } from "../lib/format";
import { useNearEnd } from "./useNearEnd";

const LABEL = {
  none: "Download",
  downloading: "Downloading",
  installed: "Installed",
  failed: "Retry download",
} as const;

/** One BeatSaver map as a large card with a large Download. */
export function VrBsCard({ map, downloads }: { map: BsMap; downloads: Downloads }) {
  const status = downloads.status(map);
  const label = LABEL[status.kind];
  const name = status.kind === "none" ? `${label} ${map.name}` : `${label}: ${map.name}`;
  const locked =
    downloads.runner.busy || status.kind === "installed" || status.kind === "downloading";
  return (
    <article className="vr-card" data-map={map.id}>
      <Cover url={map.cover_url} big />
      <div className="vr-card-body">
        <h2 className="vr-card-title">{map.name}</h2>
        <p className="vr-help">{map.mapper}</p>
        <div className="vr-card-meta">
          <LevelChips names={map.difficulties.map((d) => d.difficulty)} />
          <span>{formatDuration(map.duration)}</span>
          <span>{`${Math.round(map.rating * 100)}% liked, ${formatCount(map.upvotes)} upvotes`}</span>
        </div>
        <div className="vr-actions">
          <PreviewButton src={map.preview_url} title={map.name} />
          <button
            type="button"
            className="btn accent vr-big"
            aria-label={name}
            disabled={locked}
            onClick={() => void downloads.start([map.id])}
          >
            {label}
          </button>
        </div>
        {status.kind === "failed" && (
          <p className="vr-help" role="alert">
            {status.reason}
          </p>
        )}
      </div>
    </article>
  );
}

export interface ListProps {
  maps: BsMap[];
  pending: boolean;
  error: unknown;
  onRetry: () => void;
  hasNext: boolean;
  fetching: boolean;
  onMore: () => void;
  downloads: Downloads;
  emptyText: string;
}

/** The scrolling card grid with its loading, error and empty states and the end sentinel. */
export function VrBsList(p: ListProps) {
  const end = useNearEnd(p.onMore, p.hasNext && !p.fetching);
  const failed = p.error !== null && p.error !== undefined;
  return (
    <div className="vr-scroll">
      {p.pending && (
        <p className="vr-help" role="status">
          Loading maps
        </p>
      )}
      {failed && p.maps.length === 0 && (
        <SpecAlert spec={errorToAlert(p.error, "Could not load BeatSaver")} onRetry={p.onRetry} />
      )}
      {!p.pending && !failed && p.maps.length === 0 && !p.hasNext && (
        <p className="vr-empty">{p.emptyText}</p>
      )}
      <div className="vr-grid">
        {p.maps.map((map) => (
          <VrBsCard key={map.id} map={map} downloads={p.downloads} />
        ))}
      </div>
      <div ref={end} aria-hidden="true" />
      {p.fetching && (
        <p className="vr-help" role="status">
          Loading more maps
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Implement the playlists**

Create `frontend/src/vr/VrBsPlaylists.tsx`:

```tsx
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
import { useNearEnd } from "./useNearEnd";
import { VrBsList } from "./VrBsCard";

const PLAYLISTS = "/vr/beatsaver?view=playlists";

/** The playlist cards; Open leads to that playlist's maps. */
export function VrBsPlaylists() {
  const query = useBsPlaylists(DEFAULT_PL_STATE);
  const lists = useMemo(() => query.data?.pages.flatMap((p) => p.items) ?? [], [query.data]);
  const { fetchNextPage } = query;
  const more = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  const end = useNearEnd(more, Boolean(query.hasNextPage) && !query.isFetchingNextPage);
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
        onMore={more}
        downloads={downloads}
        emptyText="This playlist has no maps."
      />
    </>
  );
}
```

Continued in [task-15c.md](task-15c.md).
