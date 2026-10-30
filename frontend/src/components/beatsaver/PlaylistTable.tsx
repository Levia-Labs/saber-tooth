import type { ReactNode, RefObject } from "react";
import type { BsPlaylist } from "../../api/beatsaver";
import type { PlState } from "../../lib/plfilters";
import type { useColumns } from "../../lib/useColumns";
import { VirtualBody } from "../VirtualBody";
import { useVirtualList } from "../../lib/useVirtualList";
import { PlaylistHeader } from "./PlaylistHeader";
import type { PlPatch } from "./PlaylistFilterBodies";
import { SkeletonRow, type SkeletonCol } from "../SkeletonRow";
import { PlaylistRow } from "./PlaylistRow";

/** Placeholder columns with the playlist grid; no layout shift when data arrives. */
const PLAYLIST_COLS: readonly SkeletonCol[] = [
  "cover",
  "title",
  "sub",
  ["author", "short"],
  "maps",
  "rating",
  "upvotes",
  "length",
  "nps",
  "created",
  ["actions", "actions3"],
];

interface Props {
  items: BsPlaylist[];
  loading: boolean;
  hasNext: boolean;
  fetchingNext: boolean;
  /** Stop loading by scroll: a page failed. */
  paused: boolean;
  onLoadMore: () => void;
  state: PlState;
  update: PlPatch;
  busy: boolean;
  onDownloadAll: (playlist: BsPlaylist) => void;
  table: RefObject<HTMLDivElement | null>;
  columns: ReturnType<typeof useColumns>;
  empty: ReactNode;
}

/** Scroll region with a sticky header and a virtualised body; only this region scrolls. */
export function PlaylistTable(props: Props) {
  const { items, loading, hasNext, fetchingNext, paused, onLoadMore, table, columns } = props;
  const { scroller, body, virtual } = useVirtualList({
    items,
    loading,
    hasNext,
    fetchingNext,
    paused,
    onLoadMore,
    resetKey: JSON.stringify(props.state),
    anchor: true,
  });

  return (
    <div className="lib-scroll" ref={scroller} tabIndex={-1}>
      <div
        role="table"
        aria-label="BeatSaver playlists"
        aria-rowcount={items.length + 1}
        className="lib-table pl-table"
        ref={table}
        style={columns.style}
      >
        <PlaylistHeader state={props.state} update={props.update} columns={columns.api} />
        <VirtualBody
          virtual={virtual}
          bodyRef={body}
          items={items}
          busy={loading || fetchingNext}
          row={(item, i) => (
            <PlaylistRow
              playlist={item}
              index={i}
              busy={props.busy}
              onDownloadAll={props.onDownloadAll}
            />
          )}
          skeleton={(i) => <SkeletonRow index={i} cols={PLAYLIST_COLS} />}
        />
      </div>
      {!loading && items.length === 0 && !hasNext && props.empty}
    </div>
  );
}
