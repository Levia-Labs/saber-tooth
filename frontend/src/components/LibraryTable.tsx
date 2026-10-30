import type { RefObject } from "react";
import { EmptyState } from "./EmptyState";
import type { Facets, MapItem } from "../api/types";
import { useColumns } from "../lib/useColumns";
import type { LibraryState } from "../lib/urlstate";
import { Alert } from "./Alert";
import { LibraryHeader } from "./LibraryHeader";
import { LibraryRow } from "./LibraryRow";
import { SkeletonRow } from "./SkeletonRow";
import { VirtualBody } from "./VirtualBody";
import { useVirtualList } from "../lib/useVirtualList";

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
/** Scroll region with a sticky header and a virtualised body; only this region scrolls. */
export function LibraryTable(props: Props) {
  const { items, loading, hasNext, fetchingNext, nextFailed, onLoadMore } = props;
  const { table, columns } = props;
  const { scroller, body, virtual } = useVirtualList({
    items,
    loading,
    hasNext,
    fetchingNext,
    paused: nextFailed,
    onLoadMore,
    resetKey: JSON.stringify(props.state),
  });

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
        <VirtualBody
          virtual={virtual}
          bodyRef={body}
          items={items}
          busy={loading || fetchingNext}
          row={(item, i) => <LibraryRow item={item} index={i} />}
          skeleton={(i) => <SkeletonRow index={i} />}
        />
      </div>
      {empty && (
        <EmptyState
          icon={props.filtered ? "search" : "library"}
          text={props.filtered ? "No maps match these filters" : "No maps found"}
          {...(props.filtered ? {} : { hint: "Add map folders to the library, then scan them." })}
          action={
            props.filtered ? (
              <button type="button" className="btn plain" onClick={props.onClear}>
                Clear filters
              </button>
            ) : undefined
          }
        />
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
