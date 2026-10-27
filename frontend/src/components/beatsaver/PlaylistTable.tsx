import { useVirtualizer } from "@tanstack/react-virtual";
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import type { BsPlaylist } from "../../api/beatsaver";
import type { PlState } from "../../lib/plfilters";
import type { useColumns } from "../../lib/useColumns";
import { FIRST_SKELETONS, NEXT_SKELETONS, useRowEstimate } from "../LibraryTable";
import { PlaylistHeader } from "./PlaylistHeader";
import type { PlPatch } from "./PlaylistFilterBodies";
import { PlaylistRow, PlaylistSkeletonRow } from "./PlaylistRow";

const LOAD_AHEAD = 6;

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
  const scroller = useRef<HTMLDivElement>(null);
  const body = useRef<HTMLDivElement>(null);
  const [margin, setMargin] = useState(0);
  const estimate = useRowEstimate();
  const skeletons = loading ? FIRST_SKELETONS : fetchingNext ? NEXT_SKELETONS : 0;

  const virtual = useVirtualizer({
    count: items.length + skeletons,
    getScrollElement: () => scroller.current,
    estimateSize: () => estimate,
    overscan: 8,
    scrollMargin: margin,
    getItemKey: (i) => items[i]?.id ?? `skeleton-${i}`,
  });
  useEffect(() => setMargin(body.current?.offsetTop ?? 0), [estimate]);

  // Keep the viewport anchored when a loaded page sorts in above the rows being read.
  const anchor = useRef<{ id: string; start: number } | null>(null);
  useLayoutEffect(() => {
    const el = scroller.current;
    const held = anchor.current;
    if (el && held && el.scrollTop > 0) {
      const at = items.findIndex((i) => i.id === held.id);
      const start = at >= 0 ? virtual.measurementsCache[at]?.start : undefined;
      if (start !== undefined && start !== held.start) el.scrollTop += start - held.start;
    }
  }, [items, virtual]);
  useEffect(() => {
    const first = virtual.getVirtualItems().find((v) => items[v.index]);
    const item = first && items[first.index];
    anchor.current = first && item ? { id: item.id, start: first.start } : null;
  });

  const stateKey = JSON.stringify(props.state);
  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = 0;
  }, [stateKey]);

  const last = virtual.getVirtualItems().at(-1)?.index ?? -1;
  useEffect(() => {
    if (hasNext && !fetchingNext && !paused && last >= items.length - LOAD_AHEAD) onLoadMore();
  }, [hasNext, fetchingNext, paused, last, items.length, onLoadMore]);

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
        <div
          role="rowgroup"
          className="lib-body"
          ref={body}
          style={{ height: virtual.getTotalSize() }}
          aria-busy={loading || fetchingNext}
        >
          {virtual.getVirtualItems().map((v) => {
            const item = items[v.index];
            return (
              <div
                key={v.key}
                ref={virtual.measureElement}
                data-index={v.index}
                className="lib-slot"
                style={{ transform: `translateY(${v.start - virtual.options.scrollMargin}px)` }}
              >
                {item ? (
                  <PlaylistRow
                    playlist={item}
                    index={v.index}
                    busy={props.busy}
                    onDownloadAll={props.onDownloadAll}
                  />
                ) : (
                  <PlaylistSkeletonRow index={v.index} />
                )}
              </div>
            );
          })}
        </div>
      </div>
      {!loading && items.length === 0 && !hasNext && props.empty}
    </div>
  );
}
