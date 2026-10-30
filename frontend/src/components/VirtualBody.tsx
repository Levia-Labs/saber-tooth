import type { ReactNode } from "react";
import type { VirtualList } from "../lib/useVirtualList";

interface Props<T> {
  virtual: VirtualList["virtual"];
  bodyRef: VirtualList["body"];
  items: readonly T[];
  busy: boolean;
  row: (item: T, index: number) => ReactNode;
  skeleton: (index: number) => ReactNode;
}

/** The virtualised rowgroup: positioned slots holding a row, or a skeleton past the loaded items. */
export function VirtualBody<T>({ virtual, bodyRef, items, busy, row, skeleton }: Props<T>) {
  return (
    <div
      role="rowgroup"
      className="lib-body"
      ref={bodyRef}
      style={{ height: virtual.getTotalSize() }}
      aria-busy={busy}
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
            {item ? row(item, v.index) : skeleton(v.index)}
          </div>
        );
      })}
    </div>
  );
}
