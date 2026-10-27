import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useRef, useState, type RefObject } from "react";
import type { Facets, MapItem } from "../api/types";
import { useMediaQuery } from "../lib/hooks";
import { useColumns } from "../lib/useColumns";
import type { LibraryState } from "../lib/urlstate";
import { Alert } from "./Alert";
import { LibraryHeader } from "./LibraryHeader";
import { LibraryRow } from "./LibraryRow";
import { SkeletonRow } from "./SkeletonRow";

export const FIRST_SKELETONS = 14;
export const NEXT_SKELETONS = 3;
const LOAD_AHEAD = 6;

interface Props {
  items: MapItem[];
  total: number;
  /** True while the first page of the current query is loading. */
  loading: boolean;
  hasNext: boolean;
  fetchingNext: boolean;
  nextFailed: boolean;
  onLoadMore: () => void;
  state: LibraryState;
  facets: Facets | undefined;
  update: (patch: Partial<LibraryState>, replace?: boolean) => void;
  onClear: () => void;
  filtered: boolean;
  /** Ref on the table element and the column state hook result, owned by the page. */
  table: RefObject<HTMLDivElement | null>;
  columns: ReturnType<typeof useColumns>;
}

export function useRowEstimate(): number {
  const mobile = useMediaQuery("(max-width: 719px)");
  const compact = useMediaQuery("(max-width: 1099px)");
  if (mobile) return 180;
  return compact ? 92 : 72;
}

/** Scroll region with a sticky header and a virtualised body; only this region scrolls. */
export function LibraryTable(props: Props) {
  const { items, loading, hasNext, fetchingNext, nextFailed, onLoadMore } = props;
  const scroller = useRef<HTMLDivElement>(null);
  const body = useRef<HTMLDivElement>(null);
  const { table, columns } = props;
  const [margin, setMargin] = useState(0);
  const estimate = useRowEstimate();
  const skeletons = loading ? FIRST_SKELETONS : fetchingNext ? NEXT_SKELETONS : 0;
  const count = items.length + skeletons;

  const virtual = useVirtualizer({
    count,
    getScrollElement: () => scroller.current,
    estimateSize: () => estimate,
    overscan: 8,
    scrollMargin: margin,
    getItemKey: (i) => items[i]?.id ?? `skeleton-${i}`,
  });
  useEffect(() => setMargin(body.current?.offsetTop ?? 0), [estimate]);

  const stateKey = JSON.stringify(props.state);
  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = 0;
  }, [stateKey]);

  const last = virtual.getVirtualItems().at(-1)?.index ?? -1;
  useEffect(() => {
    if (hasNext && !fetchingNext && !nextFailed && last >= items.length - LOAD_AHEAD) onLoadMore();
  }, [hasNext, fetchingNext, nextFailed, last, items.length, onLoadMore]);

  const empty = !loading && items.length === 0;
  return (
    <div className="lib-scroll" ref={scroller} tabIndex={-1}>
      <div
        role="table"
        aria-label="Maps"
        aria-rowcount={props.total + 1}
        className="lib-table"
        ref={table}
        style={columns.style}
      >
        <LibraryHeader
          state={props.state}
          facets={props.facets}
          update={props.update}
          columns={columns.api}
        />
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
                  <LibraryRow item={item} index={v.index} />
                ) : (
                  <SkeletonRow index={v.index} />
                )}
              </div>
            );
          })}
        </div>
      </div>
      {empty && (
        <div className="lib-empty">
          <Alert
            variant="info"
            title={props.filtered ? "No maps match these filters" : "No maps found"}
            message={
              props.filtered
                ? "Loosen or clear the filters to see more maps."
                : "Add map folders to the library, then scan them."
            }
            actions={
              props.filtered ? (
                <button type="button" className="btn plain" onClick={props.onClear}>
                  Clear filters
                </button>
              ) : undefined
            }
          />
        </div>
      )}
      {nextFailed && (
        <div className="lib-more">
          <Alert
            variant="danger"
            title="Could not load more maps"
            message="Check your connection and try again."
            actions={
              <button type="button" className="btn plain" onClick={onLoadMore}>
                Load more
              </button>
            }
          />
        </div>
      )}
    </div>
  );
}
