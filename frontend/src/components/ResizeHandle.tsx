import { useRef, type KeyboardEvent, type PointerEvent } from "react";
import { LABELS, LIMITS, stepWidth, type ColumnKey } from "../lib/columns";
import type { ColumnsApi } from "../lib/useColumns";

interface Props {
  colKey: ColumnKey;
  columns: ColumnsApi;
}

/** Right-edge drag handle and keyboard separator for one header cell. */
export function ResizeHandle({ colKey, columns }: Props) {
  const limit = LIMITS[colKey];
  const drag = useRef<{ x: number; w: number; last: number } | null>(null);
  if (!limit) return null;
  const width = columns.widths[colKey] ?? limit.min;

  const down = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const cell = e.currentTarget.parentElement;
    const start = cell?.getBoundingClientRect().width || width;
    drag.current = { x: e.clientX, w: start, last: start };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const move = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d) return;
    d.last = d.w + e.clientX - d.x;
    columns.preview(colKey, d.last);
  };
  const up = () => {
    const d = drag.current;
    drag.current = null;
    if (d) columns.commit(colKey, d.last);
  };
  const key = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Home") {
      e.preventDefault();
      columns.reset(colKey);
      return;
    }
    const next = stepWidth(colKey, width, e.key, e.shiftKey);
    if (next === null) return;
    e.preventDefault();
    columns.commit(colKey, next);
  };

  return (
    // A focusable separator is the WAI-ARIA window-splitter pattern; the rule does not know it.
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      className="col-resize"
      role="separator"
      aria-orientation="vertical"
      aria-label={`Resize ${LABELS[colKey]} column`}
      aria-valuenow={width}
      aria-valuemin={limit.min}
      aria-valuemax={limit.max}
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
      tabIndex={0}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
      onKeyDown={key}
      onDoubleClick={() => columns.reset(colKey)}
    />
  );
}
