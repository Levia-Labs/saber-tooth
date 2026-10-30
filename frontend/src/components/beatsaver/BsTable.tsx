import type { ReactNode, RefObject } from "react";
import type { BsMap } from "../../api/beatsaver";
import { toggle } from "../../lib/urlstate";
import type { BsState } from "../../lib/bsfilters";
import type { useColumns } from "../../lib/useColumns";
import { SkeletonRow, type SkeletonCol } from "../SkeletonRow";
import { VirtualBody } from "../VirtualBody";
import { useVirtualList } from "../../lib/useVirtualList";
import { BsHeader } from "./BsHeader";
import { BsRow } from "./BsRow";
import type { Patch } from "./BsFilterBodies";
import type { RowStatus } from "./downloads";

/** Placeholder columns with the BeatSaver grid; no layout shift when data arrives. */
const BS_COLS: readonly SkeletonCol[] = [
  "select",
  "cover",
  "title",
  ["sub", "sub-pill"],
  "author",
  "levels",
  "rating",
  "upvotes",
  "length",
  "bpm",
  "tags",
  "status",
  "actions",
];

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
        <VirtualBody
          virtual={virtual}
          bodyRef={body}
          items={items}
          busy={loading || fetchingNext}
          row={(item, i) => (
            <BsRow
              item={item}
              index={i}
              selected={props.selected.has(item.id)}
              status={props.status(item)}
              onSelect={props.onSelect}
              onDownload={props.onDownload}
              activeTags={props.state.tags}
              onToggleTag={(tag) => props.update({ tags: toggle(props.state.tags, tag) })}
            />
          )}
          skeleton={(i) => <SkeletonRow index={i} cols={BS_COLS} />}
        />
      </div>
      {!loading && items.length === 0 && !hasNext && props.empty}
    </div>
  );
}
