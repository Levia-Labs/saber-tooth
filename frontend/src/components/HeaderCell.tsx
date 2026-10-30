import type { ReactNode } from "react";
import { isResizable, type ColumnKey } from "../lib/columns";
import type { ColumnsApi } from "../lib/useColumns";
import { Icon } from "./icons";
import { ResizeHandle } from "./ResizeHandle";
import { Tip } from "./Tip";

interface Props {
  /** Column key for the `col-` class and resize handle; omit for a plain header. */
  col?: ColumnKey;
  label: string;
  columns?: ColumnsApi;
  /** Class prefix of the column: `col` (default) or `jc` for the jobs grid. */
  prefix?: string;
  /** Visually quiet header; defaults to the cover column. */
  quiet?: boolean;
  /** Sortable columns pass `onSort`; `order` is the active direction when this column is sorted. */
  onSort?: () => void;
  order?: "asc" | "desc" | undefined;
  /** Tooltip on the sort button; none when omitted. */
  tip?: string;
  filter?: ReactNode;
}

/** One column header: label or sort button, optional filter, sort indicator, resize handle. */
export function HeaderCell(p: Props) {
  const { col, label, columns, onSort, order, tip, filter } = p;
  const quiet = p.quiet ?? col === "cover";
  const named = col ? ` ${p.prefix ?? "col"}-${col}` : "";
  const aria = order ? (order === "asc" ? "ascending" : "descending") : "none";
  const button = (
    <button type="button" className="th-sort" onClick={onSort} aria-label={`Sort by ${label}`}>
      <span className="th-label">{label}</span>
    </button>
  );
  return (
    <div
      className={`th${named}${quiet ? " th-quiet" : ""}`}
      role="columnheader"
      aria-sort={onSort ? aria : undefined}
    >
      <div className="th-row">
        {onSort ? (
          tip ? (
            <Tip text={tip}>{button}</Tip>
          ) : (
            button
          )
        ) : (
          <span className="th-label">{label}</span>
        )}
        {filter}
        {onSort && (
          <span className="th-slot" aria-hidden="true">
            {order && <Icon name={order === "asc" ? "sort-asc" : "sort-desc"} />}
          </span>
        )}
      </div>
      {col && columns && isResizable(col) && <ResizeHandle colKey={col} columns={columns} />}
    </div>
  );
}
