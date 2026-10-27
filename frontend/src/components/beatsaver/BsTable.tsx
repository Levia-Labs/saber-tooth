import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import type { BsMap } from "../../api/beatsaver";
import type { BsState } from "../../lib/bsfilters";
import type { useColumns } from "../../lib/useColumns";
import { FIRST_SKELETONS, NEXT_SKELETONS, useRowEstimate } from "../LibraryTable";
import { BsHeader } from "./BsHeader";
import { BsRow } from "./BsRow";
import { BsSkeletonRow } from "./BsSkeletonRow";
import type { Patch } from "./BsFilterBodies";
import type { RowStatus } from "./downloads";

const LOAD_AHEAD = 6;

interface Props {
  items: BsMap[];
  loading: boolean;
  hasNext: boolean;
  fetchingNext: boolean;
  /** Stop loading by scroll: a page failed or BeatSaver asked us to wait. */
  paused: boolean;
  onLoadMore: () => void;
  state: BsState;
  update: Patch;
  selected: ReadonlySet<string>;
  status: (item: BsMap) => RowStatus;
  onSelect: (item: BsMap) => void;
  onSelectAll: () => void;
  onDownload: (id: string) => void;
  table: RefObject<HTMLDivElement | null>;
  columns: ReturnType<typeof useColumns>;
  empty: ReactNode;
}

/** Scroll region with a sticky header and a virtualised body; only this region scrolls. */
export function BsTable(props: Props) {
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

  const stateKey = JSON.stringify(props.state);
  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = 0;
  }, [stateKey]);

  const last = virtual.getVirtualItems().at(-1)?.index ?? -1;
  useEffect(() => {
    if (hasNext && !fetchingNext && !paused && last >= items.length - LOAD_AHEAD) onLoadMore();
  }, [hasNext, fetchingNext, paused, last, items.length, onLoadMore]);

  const allSelected = items.length > 0 && items.every((i) => props.selected.has(i.id));
  return (
    <div className="lib-scroll" ref={scroller} tabIndex={-1}>
      <div
        role="table"
        aria-label="BeatSaver maps"
        aria-rowcount={items.length + 1}
        className="lib-table bs-table"
        ref={table}
        style={columns.style}
      >
        <BsHeader
          state={props.state}
          update={props.update}
          columns={columns.api}
          allSelected={allSelected}
          onSelectAll={props.onSelectAll}
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
                  <BsRow
                    item={item}
                    index={v.index}
                    selected={props.selected.has(item.id)}
                    status={props.status(item)}
                    onSelect={props.onSelect}
                    onDownload={props.onDownload}
                  />
                ) : (
                  <BsSkeletonRow index={v.index} />
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
