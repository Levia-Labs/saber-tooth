import { useVirtualizer, type Virtualizer } from "@tanstack/react-virtual";
import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { CARD_QUERY, COMPACT_QUERY } from "./breakpoint";
import { useMediaQuery } from "./hooks";

export const FIRST_SKELETONS = 14;
export const NEXT_SKELETONS = 3;
const LOAD_AHEAD = 6;

export function useRowEstimate(): number {
  const mobile = useMediaQuery(CARD_QUERY);
  const compact = useMediaQuery(COMPACT_QUERY);
  if (mobile) return 140;
  return compact ? 92 : 72;
}

interface Options {
  items: readonly { id: string }[];
  loading: boolean;
  hasNext: boolean;
  fetchingNext: boolean;
  /** Stop loading by scroll: a page failed or the server asked us to wait. */
  paused: boolean;
  onLoadMore: () => void;
  /** Scroll returns to the top when this changes. */
  resetKey: unknown;
  /** Keep the viewport anchored when a loaded page sorts in above the rows being read. */
  anchor?: boolean;
}

export interface VirtualList {
  scroller: RefObject<HTMLDivElement | null>;
  body: RefObject<HTMLDivElement | null>;
  virtual: Virtualizer<HTMLDivElement, Element>;
}

/** Virtualised rows with skeleton tail, scroll reset, load-ahead and optional scroll anchoring. */
export function useVirtualList(o: Options): VirtualList {
  const { items, loading, hasNext, fetchingNext, paused, onLoadMore } = o;
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

  const held = useRef<{ id: string; start: number } | null>(null);
  const anchored = o.anchor === true;
  useLayoutEffect(() => {
    const el = scroller.current;
    const was = held.current;
    if (anchored && el && was && el.scrollTop > 0) {
      const at = items.findIndex((i) => i.id === was.id);
      const start = at >= 0 ? virtual.measurementsCache[at]?.start : undefined;
      if (start !== undefined && start !== was.start) el.scrollTop += start - was.start;
    }
  }, [anchored, items, virtual]);
  useEffect(() => {
    if (!anchored) return;
    const first = virtual.getVirtualItems().find((v) => items[v.index]);
    const item = first && items[first.index];
    held.current = first && item ? { id: item.id, start: first.start } : null;
  });

  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = 0;
  }, [o.resetKey]);

  const last = virtual.getVirtualItems().at(-1)?.index ?? -1;
  useEffect(() => {
    if (hasNext && !fetchingNext && !paused && last >= items.length - LOAD_AHEAD) onLoadMore();
  }, [hasNext, fetchingNext, paused, last, items.length, onLoadMore]);

  return { scroller, body, virtual };
}
