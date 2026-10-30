import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { useCallback, useMemo, useRef } from "react";
import { useDownloads } from "../components/beatsaver/downloads";
import { useNarrow } from "./breakpoint";
import { useListScroll } from "./listscroll";
import { useColumns } from "./useColumns";

interface Page<T> {
  items: T[];
  partial?: boolean;
  retry_after?: number | null;
}

type ColumnSet = Parameters<typeof useColumns>[1];

/**
 * Shared plumbing of the BeatSaver lists: table ref and columns, narrow flag, downloads, page
 * flattening with a caller `select` (memoise it), scroll-load, retry and the paused flag
 * (a page failed or BeatSaver asked us to wait).
 */
export function useInfiniteList<T, P extends Page<T>>(
  query: UseInfiniteQueryResult<InfiniteData<P>, unknown>,
  columnSet: ColumnSet,
  select: (all: T[]) => T[],
) {
  const table = useRef<HTMLDivElement>(null);
  const columns = useColumns(table, columnSet);
  const narrow = useNarrow();
  const downloads = useDownloads();
  const { fetchNextPage, hasNextPage, isFetchingNextPage, isFetchNextPageError, refetch } = query;

  const pages = query.data?.pages;
  const items = useMemo(() => select(pages?.flatMap((p) => p.items) ?? []), [pages, select]);
  const lastPage = pages?.at(-1);
  const limited = Boolean(lastPage && (lastPage.partial || lastPage.retry_after));
  const paused = limited || isFetchNextPageError;

  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  useListScroll(!query.isPending, items.length, hasNextPage, {
    load: loadMore,
    busy: isFetchingNextPage || paused,
  });
  const retry = useCallback(
    () => void (hasNextPage ? fetchNextPage() : refetch()),
    [hasNextPage, fetchNextPage, refetch],
  );
  const failedFirst = query.isError && !query.data;
  return {
    table,
    columns,
    narrow,
    downloads,
    items,
    lastPage,
    limited,
    paused,
    loadMore,
    retry,
    failedFirst,
  };
}
